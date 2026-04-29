import csv
import json
import re

from django.http import HttpResponse
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from core.jwt import ExportRateThrottle
from core.scoping import PlantScopedQuerysetMixin
from .models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
    QuestionnaireTemplate,
    SupplierQuestionnaire,
)
from .permissions import SupplierPermission
from .serializers import (
    SupplierAssessmentSerializer,
    SupplierEvaluationConfigSerializer,
    SupplierInternalEvaluationSerializer,
    SupplierSerializer,
    QuestionnaireTemplateSerializer,
    SupplierQuestionnaireSerializer,
)


class SupplierViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [SupplierPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["risk_level", "risk_adj", "status", "nis2_relevant"]
    search_fields = ["name", "vat_number"]
    # Supplier ha M2M `plants`; supplier senza alcun plant assegnato = cross-plant
    # (fornitore organizzativo) → visibile a tutti gli utenti con almeno un accesso.
    plant_field = "plants"
    allow_null_plant = True

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

    @action(detail=True, methods=["post"], url_path="nda/upload")
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
            status="approvato",
            supplier=supplier,
            plant=None,
            expiry_date=expiry_date,
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

    @action(detail=False, methods=["post"], url_path="suggest-cpv")
    def suggest_cpv(self, request):
        """
        POST /suppliers/suggest-cpv/
        Body: {description: str}
        Invia la descrizione (sanitizzata, senza nome fornitore) all'AI e restituisce
        una lista di codici CPV suggeriti con descrizione.
        Human-in-the-loop: l'output è sempre revisionato dall'utente prima dell'applicazione.
        """
        from apps.ai_engine.router import route
        from apps.ai_engine.sanitizer import Sanitizer

        description = (request.data.get("description") or "").strip()
        if not description:
            return Response({"error": "La descrizione è obbligatoria."}, status=400)
        if len(description) > 2000:
            return Response({"error": "La descrizione non può superare 2000 caratteri."}, status=400)

        sanitizer = Sanitizer()
        sanitized_ctx, _ = sanitizer.sanitize({"text": description})
        safe_description = sanitized_ctx["text"]

        system = (
            "Sei un esperto di appalti pubblici europei. "
            "Rispondi SOLO con un array JSON valido. "
            "Non aggiungere testo prima o dopo il JSON."
        )
        prompt = (
            f"Sulla base di questa descrizione di fornitura:\n\n\"{safe_description}\"\n\n"
            "Suggerisci i 3-5 codici CPV (Common Procurement Vocabulary) più appropriati "
            "secondo il Regolamento (CE) n. 213/2008 e successivi aggiornamenti. "
            "Rispondi ESCLUSIVAMENTE con un array JSON nel formato:\n"
            '[{"code": "XXXXXXXX-Y", "label": "Descrizione in italiano"}]\n'
            "REQUISITI OBBLIGATORI sul codice:\n"
            "- Formato standard CPV completo: 8 cifre + trattino + 1 cifra di controllo (es. 79211100-0, 72000000-5, 50000000-5).\n"
            "- La cifra di controllo Y NON è arbitraria: è quella ufficiale assegnata dall'UE al codice nel catalogo CPV. "
            "Non inventare la cifra di controllo: se non sei certo, NON includere il codice.\n"
            "- Restituisci esclusivamente codici CPV reali, presenti nel catalogo ufficiale.\n"
            "Non aggiungere altro testo prima o dopo l'array JSON."
        )

        try:
            result = route(
                task_type="cpv_suggestion",
                prompt=prompt,
                system=system,
                user=request.user,
                module_source="M14",
                sanitize=False,  # già sanitizzato manualmente sopra
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=503)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("suggest_cpv AI error: %s", exc)
            return Response(
                {"error": f"Errore AI ({type(exc).__name__}): controlla la configurazione AI Engine o il budget disponibile."},
                status=503,
            )

        raw_text = result.get("text", "")
        suggestions = []
        # Pattern CPV standard: 8 cifre + trattino + 1 cifra di controllo (Reg. CE 213/2008).
        # La cifra di controllo è assegnata dall'UE nel catalogo ufficiale e NON è calcolabile
        # né defaultabile: se l'AI non la fornisce, scartiamo il suggerimento.
        cpv_re = re.compile(r"^\d{8}-\d$")
        try:
            # Estrai solo il JSON dall'output (l'AI potrebbe aggiungere testo)
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            if start >= 0 and end > start:
                raw_suggestions = json.loads(raw_text[start:end])
                for item in raw_suggestions:
                    if not isinstance(item, dict) or "code" not in item:
                        continue
                    code = str(item["code"]).strip()
                    if cpv_re.match(code):
                        suggestions.append({"code": code, "label": item.get("label", "")})
        except (json.JSONDecodeError, ValueError):
            pass

        log_action(
            user=request.user,
            action_code="suppliers.cpv.suggest",
            level="L1",
            entity=request.user,
            payload={
                "description_len": len(description),
                "suggestions_count": len(suggestions),
                "interaction_id": result.get("interaction_id"),
            },
        )

        return Response({
            "suggestions": suggestions,
            "interaction_id": result.get("interaction_id"),
            "provider": result.get("provider"),
        })

    @action(
        detail=False, methods=["get"], url_path="export-csv",
        throttle_classes=[ExportRateThrottle],
    )
    def export_csv(self, request):
        """
        GET /suppliers/export-csv/?nis2_only=true
        Esporta i fornitori in CSV con tutti i campi richiesti da ACN Delibera 127434.
        """
        nis2_only = request.query_params.get("nis2_only", "false").lower() == "true"
        qs = Supplier.objects.filter(deleted_at__isnull=True).order_by("name")
        if nis2_only:
            qs = qs.filter(nis2_relevant=True)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = "fornitori_nis2.csv" if nis2_only else "fornitori.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")  # BOM per Excel

        CRITERION_LABELS = {
            "ict": "Fornitura ICT strutturale (a)",
            "non_fungibile": "Non fungibilità (b)",
            "entrambi": "Entrambi (a+b)",
            "": "",
        }
        THRESHOLD_LABELS = {
            "bassa": "Bassa (<20%)",
            "media": "Media (20-50%)",
            "critica": "Critica (>50%)",
            "nd": "N/D",
        }

        writer = csv.writer(response)
        writer.writerow([
            "Denominazione",
            "Codice Fiscale / P.IVA",
            "Paese sede legale",
            "Codici CPV",
            "Descrizione CPV",
            "Rilevante NIS2",
            "Criterio rilevanza NIS2",
            "% Concentrazione fornitura",
            "Soglia TPRM",
            "Livello rischio TPRM",
            "Stato",
            "Data ultima valutazione",
            "Email",
        ])

        for s in qs:
            cpv_codes_str = "; ".join(
                (c.get("code", "") if isinstance(c, dict) else str(c))
                for c in (s.cpv_codes or [])
            )
            cpv_labels_str = "; ".join(
                (c.get("label", "") if isinstance(c, dict) else "")
                for c in (s.cpv_codes or [])
            )
            writer.writerow([
                s.name,
                s.vat_number,
                s.country,
                cpv_codes_str,
                cpv_labels_str,
                "Sì" if s.nis2_relevant else "No",
                CRITERION_LABELS.get(s.nis2_relevance_criterion, s.nis2_relevance_criterion),
                f"{s.supply_concentration_pct}%" if s.supply_concentration_pct is not None else "",
                THRESHOLD_LABELS.get(s.concentration_threshold, ""),
                s.risk_level,
                s.status,
                str(s.evaluation_date) if s.evaluation_date else "",
                s.email,
            ])

        log_action(
            user=request.user,
            action_code="suppliers.export.csv",
            level="L2",
            entity=request.user,
            payload={"nis2_only": nis2_only, "count": qs.count()},
        )
        return response

    @action(detail=True, methods=["get", "post"], url_path="internal-evaluation")
    def internal_evaluation(self, request, pk=None):
        """
        GET  /suppliers/<id>/internal-evaluation/  → valutazione corrente (is_current=True) o 404 se assente.
        POST /suppliers/<id>/internal-evaluation/  → crea nuova valutazione (marca la precedente come storico).
        """
        from django.core.exceptions import ValidationError
        from .services import create_internal_evaluation

        supplier = self.get_object()

        if request.method == "GET":
            current = SupplierInternalEvaluation.objects.filter(
                supplier=supplier, is_current=True, deleted_at__isnull=True
            ).first()
            if not current:
                return Response({"detail": "Nessuna valutazione interna corrente."}, status=404)
            return Response(SupplierInternalEvaluationSerializer(current).data)

        scores = {
            "impatto": request.data.get("score_impatto"),
            "accesso": request.data.get("score_accesso"),
            "dati": request.data.get("score_dati"),
            "dipendenza": request.data.get("score_dipendenza"),
            "integrazione": request.data.get("score_integrazione"),
            "compliance": request.data.get("score_compliance"),
        }
        try:
            scores = {k: int(v) for k, v in scores.items() if v is not None}
        except (TypeError, ValueError):
            return Response({"error": "Score devono essere interi 1–5."}, status=400)

        notes = request.data.get("notes", "")
        try:
            ev = create_internal_evaluation(supplier, scores, request.user, notes=notes)
        except ValidationError as exc:
            return Response({"error": exc.messages if hasattr(exc, "messages") else str(exc)}, status=400)
        return Response(SupplierInternalEvaluationSerializer(ev).data, status=201)

    @action(detail=True, methods=["get"], url_path="internal-evaluation/history")
    def internal_evaluation_history(self, request, pk=None):
        """GET /suppliers/<id>/internal-evaluation/history/ — storico completo valutazioni interne."""
        supplier = self.get_object()
        qs = SupplierInternalEvaluation.objects.filter(
            supplier=supplier, deleted_at__isnull=True
        ).order_by("-evaluated_at")
        data = SupplierInternalEvaluationSerializer(qs, many=True).data
        return Response({"results": data, "count": len(data)})

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


class SupplierEvaluationConfigView(APIView):
    """
    GET  /suppliers/evaluation-config/  → restituisce la config corrente (read = ruoli governance fornitori).
    PUT  /suppliers/evaluation-config/  → aggiorna pesi/label/soglie (write = solo super_admin GRC).
    """
    permission_classes = [SupplierPermission]

    def get(self, request):
        config = SupplierEvaluationConfig.get_solo()
        return Response(SupplierEvaluationConfigSerializer(config).data)

    def put(self, request):
        from apps.auth_grc.permissions import IsGrcSuperAdmin

        if not IsGrcSuperAdmin().has_permission(request, self):
            return Response(
                {"error": "Solo super_admin GRC possono modificare la configurazione."},
                status=403,
            )

        config = SupplierEvaluationConfig.get_solo()
        serializer = SupplierEvaluationConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)

        log_action(
            user=request.user,
            action_code="suppliers.evaluation_config.update",
            level="L1",
            entity=config,
            payload={
                "weights": config.weights,
                "risk_thresholds": config.risk_thresholds,
                "assessment_validity_months": config.assessment_validity_months,
                "nis2_concentration_bump": config.nis2_concentration_bump,
            },
        )
        return Response(serializer.data)


class SupplierAssessmentViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SupplierAssessment.objects.filter(
        deleted_at__isnull=True
    ).select_related("supplier", "assessed_by", "reviewed_by")
    serializer_class = SupplierAssessmentSerializer
    permission_classes = [SupplierPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["supplier"]
    plant_field = "supplier__plants"
    allow_null_plant = True  # supplier organizzativi (no plants) restano visibili

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="suppliers.assessment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "supplier_id": str(instance.supplier_id)},
        )

    def destroy(self, request, *args, **kwargs):
        from .risk_adj import recompute_risk_adj
        instance = self.get_object()
        supplier = instance.supplier
        instance.soft_delete()
        recompute_risk_adj(supplier)
        log_action(
            user=request.user,
            action_code="suppliers.assessment.delete",
            level="L2",
            entity=instance,
            payload={
                "supplier_id": str(supplier.id),
                "supplier_name": supplier.name,
                "status": instance.status,
            },
        )
        return Response(status=204)

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
    permission_classes = [SupplierPermission]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=204)


class SupplierQuestionnaireViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SupplierQuestionnaire.objects.filter(
        deleted_at__isnull=True
    ).select_related("supplier", "template", "sent_by")
    serializer_class = SupplierQuestionnaireSerializer
    permission_classes = [SupplierPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["supplier", "status"]
    plant_field = "supplier__plants"
    allow_null_plant = True

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
