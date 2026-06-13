from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.viewsets import SoftDeleteAuditMixin
from ..models import Control, ControlDomain, Framework
from ..permissions import FrameworkPermission
from ..serializers import (
    ControlDomainSerializer,
    ControlSerializer,
    FrameworkSerializer,
)


class FrameworkViewSet(viewsets.ModelViewSet):
    serializer_class   = FrameworkSerializer
    permission_classes = [FrameworkPermission]

    def get_queryset(self):
        plant_id = self.request.query_params.get("plant")
        if plant_id:
            from apps.plants.services import get_active_frameworks
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
            if plant:
                return get_active_frameworks(plant)
        return Framework.objects.filter(archived_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from ..services import archive_framework

        fw = self.get_object()
        try:
            archive_framework(fw, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_framework(self, request, pk=None):
        from django.core.exceptions import ValidationError

        from ..services import delete_framework

        fw = self.get_object()
        try:
            delete_framework(fw, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="governance")
    def governance_list(self, request):
        """
        Governance list: framework metadata + counts + available languages.
        """
        from ..services import list_framework_governance_metadata
        return Response({"results": list_framework_governance_metadata()})

    @action(
        detail=False,
        methods=["post"],
        url_path="import-preview",
    )
    def import_preview(self, request):
        """
        Preview import (validate + summary). Expects JSON body.
        """
        from django.utils.translation import gettext as _
        from django.core.exceptions import ValidationError
        from ..services import preview_framework_import

        if not request.user.is_superuser:
            return Response({"error": _("Solo il superuser può importare framework.")}, status=403)
        try:
            return Response(preview_framework_import(request.data))
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
    )
    def import_framework(self, request):
        """
        Import framework JSON. Expects JSON body with optional 'sha256' for confirmation.
        """
        from django.utils.translation import gettext as _
        from django.core.exceptions import ValidationError
        from ..services import preview_framework_import, import_framework_payload

        if not request.user.is_superuser:
            return Response({"error": _("Solo il superuser può importare framework.")}, status=403)

        # If client sends sha256, verify matches preview for the provided payload
        client_sha = request.data.get("sha256")
        payload = dict(request.data)
        payload.pop("sha256", None)
        try:
            preview = preview_framework_import(payload)
            if client_sha and client_sha != preview.get("sha256"):
                return Response({"error": _("Conferma import non valida (sha256 mismatch).")}, status=400)
            return Response(import_framework_payload(payload, request.user))
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)


class ControlDomainViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    queryset = ControlDomain.objects.select_related("framework")
    serializer_class = ControlDomainSerializer
    permission_classes = [FrameworkPermission]
    audit_action = "controls.control_domain"


class ControlViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    queryset = Control.objects.select_related("framework", "domain")
    serializer_class = ControlSerializer
    permission_classes = [FrameworkPermission]
    # Il default destroy faceva hard delete del Control → CASCADE su TUTTE le
    # ControlInstance valutate (FK on_delete=CASCADE), perdita dati su tutti i
    # siti. Ora soft delete + audit; le istanze restano (filtrate dal proprio
    # deleted_at). Il catalogo si gestisce via load_frameworks.
    audit_action = "controls.control"

    @action(detail=True, methods=["post"], url_path="explain")
    def explain(self, request, pk=None):
        """
        Genera (o rigenera) la spiegazione plain-language del controllo via AI.
        Body: { "lang": "it" }
        """
        from apps.ai_engine.tasks_ai import explain_control
        from django.utils.translation import gettext as _

        control = self.get_object()
        lang = request.data.get("lang", "it")
        try:
            result = explain_control(control, lang, request.user)
            return Response(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"explain_control error: {e}")
            return Response({"error": _("Generazione spiegazione non riuscita: %(err)s") % {"err": str(e)}}, status=500)

    @action(detail=True, methods=["post"], url_path="generate-document")
    def generate_document(self, request, pk=None):
        """
        Genera un documento .docx di procedura operativa per il controllo via AI.
        Body: { "lang": "it" }
        """
        import logging
        from django.http import HttpResponse
        from django.utils.translation import gettext as _
        from core.audit import log_action
        from ..services import generate_procedure_document

        control = self.get_object()
        lang = request.data.get("lang", "it")
        try:
            docx_bytes = generate_procedure_document(control, lang, request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logging.getLogger(__name__).error(f"generate_document error [{control.external_id}]: {e}")
            return Response(
                {"error": _("Generazione documento non riuscita: %(err)s") % {"err": str(e)}},
                status=500,
            )

        log_action(
            user=request.user,
            action_code="control.document_generated",
            level="L1",
            entity=control,
            payload={"lang": lang},
        )

        filename = f"{control.external_id}_procedura.docx"
        response = HttpResponse(
            docx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
