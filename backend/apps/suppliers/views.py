from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import Supplier, SupplierAssessment, QuestionnaireTemplate, SupplierQuestionnaire
from .serializers import (
    SupplierAssessmentSerializer,
    SupplierSerializer,
    QuestionnaireTemplateSerializer,
    SupplierQuestionnaireSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["risk_level", "status"]
    search_fields = ["name", "vat_number"]

    @action(detail=True, methods=["get"], url_path="nda")
    def nda_list(self, request, pk=None):
        """GET /suppliers/<id>/nda/ — lista documenti NDA/contratto collegati al fornitore."""
        from apps.documents.models import Document
        supplier = self.get_object()
        docs = Document.objects.filter(
            supplier=supplier,
            document_type="contratto",
            deleted_at__isnull=True,
        ).order_by("-created_at")
        data = [
            {
                "id": str(d.id),
                "title": d.title,
                "status": d.status,
                "expiry_date": str(d.expiry_date) if d.expiry_date else None,
                "review_due_date": str(d.review_due_date) if d.review_due_date else None,
                "created_at": d.created_at.date().isoformat(),
                "has_file": d.versions.exists(),
                "latest_version": self._version_info(d),
            }
            for d in docs
        ]
        return Response({"results": data, "count": len(data)})

    @action(detail=True, methods=["post"], url_path="nda/upload", parser_classes=None)
    def nda_upload(self, request, pk=None):
        """
        POST /suppliers/<id>/nda/upload/
        multipart/form-data: file, title, expiry_date (opt), notes (opt)
        Crea un Document con document_type="contratto" collegato al fornitore.
        """
        from apps.documents.models import Document
        from apps.documents.services import add_version_with_file
        from rest_framework.parsers import MultiPartParser, FormParser
        from core.audit import log_action
        import datetime

        supplier = self.get_object()
        uploaded_file = request.FILES.get("file")
        title = request.data.get("title", "").strip()
        expiry_date_str = request.data.get("expiry_date", "")
        notes = request.data.get("notes", "")

        if not uploaded_file:
            return Response({"error": "Il file è obbligatorio."}, status=400)
        if not title:
            return Response({"error": "Il titolo è obbligatorio."}, status=400)

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.date.fromisoformat(expiry_date_str)
            except ValueError:
                return Response({"error": "Formato data non valido (YYYY-MM-DD)."}, status=400)

        doc = Document.objects.create(
            title=title,
            category="contratto",
            document_type="contratto",
            status="bozza",
            supplier=supplier,
            plant=None,
            expiry_date=expiry_date,
            notes=notes,
            owner=request.user,
            created_by=request.user,
        )

        try:
            add_version_with_file(doc, uploaded_file, request.user, change_summary="Caricamento iniziale NDA")
        except Exception as e:
            doc.delete()
            return Response({"error": str(e)}, status=400)

        log_action(
            user=request.user,
            action_code="suppliers.nda.upload",
            level="L2",
            entity=doc,
            payload={
                "supplier_id": str(supplier.id),
                "supplier_name": supplier.name,
                "document_id": str(doc.id),
                "title": title,
                "expiry_date": expiry_date_str or None,
            },
        )

        return Response({
            "id": str(doc.id),
            "title": doc.title,
            "status": doc.status,
            "expiry_date": str(doc.expiry_date) if doc.expiry_date else None,
            "created_at": doc.created_at.date().isoformat(),
        }, status=201)

    def _version_info(self, doc):
        v = doc.versions.first()
        if not v:
            return None
        return {
            "file_name": v.file_name,
            "file_size": v.file_size,
            "sha256": v.sha256[:12] + "…",
            "version_number": v.version_number,
        }

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="suppliers.supplier.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )

    def destroy(self, request, *args, **kwargs):
        from django.utils import timezone as tz
        instance = self.get_object()
        # Cascade soft-delete questionnaires
        instance.questionnaires.filter(deleted_at__isnull=True).update(deleted_at=tz.now())
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="suppliers.supplier.delete",
            level="L2",
            entity=instance,
            payload={"name": instance.name},
        )
        return Response(status=204)


class SupplierAssessmentViewSet(viewsets.ModelViewSet):
    queryset = SupplierAssessment.objects.all()
    serializer_class = SupplierAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["supplier"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="suppliers.assessment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "supplier_id": str(instance.supplier_id)},
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        from .services import complete_assessment
        assessment = self.get_object()
        result = complete_assessment(
            assessment,
            request.user,
            score_overall=request.data.get("score_overall"),
            score_governance=request.data.get("score_governance"),
            score_security=request.data.get("score_security"),
            score_bcp=request.data.get("score_bcp"),
            findings=request.data.get("findings", ""),
        )
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import approve_assessment
        assessment = self.get_object()
        try:
            result = approve_assessment(assessment, request.user, notes=request.data.get("notes", ""))
            return Response({"ok": True, "status": result.status})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import reject_assessment
        assessment = self.get_object()
        try:
            result = reject_assessment(assessment, request.user, notes=request.data.get("notes", ""))
            return Response({"ok": True, "status": result.status})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)


class QuestionnaireTemplateViewSet(viewsets.ModelViewSet):
    queryset = QuestionnaireTemplate.objects.filter(deleted_at__isnull=True)
    serializer_class = QuestionnaireTemplateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=204)


class SupplierQuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = SupplierQuestionnaire.objects.filter(
        deleted_at__isnull=True
    ).select_related("supplier", "template", "sent_by")
    serializer_class = SupplierQuestionnaireSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["supplier", "status"]

    @action(detail=False, methods=["post"], url_path="send")
    def send_questionnaire(self, request):
        from django.core.exceptions import ValidationError
        from .services import send_questionnaire

        supplier_id = request.data.get("supplier_id")
        template_id = request.data.get("template_id")

        if not supplier_id or not template_id:
            return Response({"error": "supplier_id e template_id obbligatori."}, status=400)

        try:
            supplier = Supplier.objects.get(pk=supplier_id)
            template = QuestionnaireTemplate.objects.get(pk=template_id, deleted_at__isnull=True)
            q = send_questionnaire(supplier, template, request.user)
            return Response(SupplierQuestionnaireSerializer(q).data, status=201)
        except (Supplier.DoesNotExist, QuestionnaireTemplate.DoesNotExist):
            return Response({"error": "Fornitore o template non trovato."}, status=404)
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="resend")
    def resend(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import resend_questionnaire

        q = self.get_object()
        try:
            result = resend_questionnaire(q, request.user)
            return Response(SupplierQuestionnaireSerializer(result).data)
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import register_evaluation

        q = self.get_object()
        evaluation_date_str = request.data.get("evaluation_date")
        risk_result = request.data.get("risk_result")
        notes = request.data.get("notes", "")

        if not evaluation_date_str or not risk_result:
            return Response({"error": "evaluation_date e risk_result obbligatori."}, status=400)

        try:
            from datetime import date
            evaluation_date = date.fromisoformat(evaluation_date_str)
            result = register_evaluation(q, evaluation_date, risk_result, request.user, notes)
            return Response(SupplierQuestionnaireSerializer(result).data)
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)
        except ValueError:
            return Response({"error": "Formato data non valido (YYYY-MM-DD)."}, status=400)
