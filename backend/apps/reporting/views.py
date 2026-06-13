from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.scoping import require_plant_access

from . import services
from .permissions import AccessReviewPermission, ReportingPermission


class PlantParamGuardedView(APIView):
    """I report costruiscono la risposta direttamente dal `?plant=` richiesto,
    senza passare da un queryset scoped: il check di accesso al sito va fatto
    qui (sweep security 2026-06-12). Senza plant il report è aggregato su
    tutti i siti → solo scope org."""

    permission_classes = [ReportingPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_plant_access(request.user, request.query_params.get("plant"))


def _resolve_lang(request) -> str:
    """Lingua dal query param ?lang o dall'header Accept-Language, default 'it'."""
    from apps.tasks.kpi_catalog import LANGS

    lang = (request.query_params.get("lang") or "").lower()
    if lang in LANGS:
        return lang
    accept = request.headers.get("Accept-Language", "")
    if accept:
        first = accept.split(",")[0].strip().lower()[:2]
        if first in LANGS:
            return first
    return "it"


class ComplianceSummaryView(PlantParamGuardedView):
    """
    GET /api/v1/reporting/compliance/?plant=<uuid>&framework=<code>

    Riusa `apps.controls.services.get_compliance_summary` per garantire
    coerenza con la dashboard e con il govrico Assistant.
    """

    def get(self, request):
        return Response(services.compliance_summary(
            request.query_params.get("plant"),
            request.query_params.get("framework"),
        ))


class RiskSummaryView(PlantParamGuardedView):
    def get(self, request):
        return Response(services.risk_summary(request.query_params.get("plant")))


class IncidentSummaryView(PlantParamGuardedView):
    def get(self, request):
        return Response(services.incident_summary(request.query_params.get("plant")))


class OwnerReportView(PlantParamGuardedView):
    def get(self, request):
        return Response(services.owner_report(request.query_params.get("plant")))


class KpiTrendView(PlantParamGuardedView):
    def get(self, request):
        return Response(services.kpi_trend(
            request.query_params.get("plant"),
            request.query_params.get("framework", "ISO27001"),
            request.query_params.get("weeks", 12),
        ))


class RiskBiaBcpView(PlantParamGuardedView):
    """
    Endpoint unificato Risk + BIA + BCP per il tab dedicato nel Reporting.
    GET /reporting/risk-bia-bcp/?plant=<uuid>
    """

    def get(self, request):
        return Response(services.risk_bia_bcp(request.query_params.get("plant")))


class AccessMatrixView(PlantParamGuardedView):
    """GET /api/v1/reporting/access-matrix/?plant=&lang=  (+ &format=csv)

    Matrice Accessi & Responsabilità per la user-access review (ISO 27001
    A.9.2.5): chi ha accesso e chi è responsabile di cosa, con flag di
    incoerenza. Ristretta a governance/audit."""

    permission_classes = [AccessReviewPermission]

    def get(self, request):
        lang = _resolve_lang(request)
        data = services.access_matrix(request.query_params.get("plant"), lang=lang)
        # NB: `export` e non `format` (quest'ultimo collide con la content
        # negotiation di DRF e darebbe 404).
        if request.query_params.get("export") == "csv":
            return self._csv(data, lang)
        return Response(data)

    def _csv(self, data, lang):
        import io

        from django.http import HttpResponse
        from django.utils.translation import gettext, override

        from core.csv_safe import safe_writer

        buf = io.StringIO()
        w = safe_writer(buf)
        with override(lang):
            w.writerow([
                gettext("Utente"), gettext("Email"), gettext("Attivo"),
                gettext("Tipo"), gettext("Ruolo"), gettext("Perimetro"),
                gettext("Siti"), gettext("Scadenza"), gettext("Segnalazioni"),
            ])
            for r in data["rows"]:
                w.writerow([
                    r["user_name"], r["user_email"],
                    gettext("Sì") if r["is_active"] else gettext("No"),
                    gettext("Accesso") if r["kind"] == "access" else gettext("Responsabilità"),
                    r["role_label"], r["scope_label"],
                    gettext("Tutti i siti") if r["covers_all"] else ", ".join(r["plant_codes"]),
                    r["valid_until"] or "",
                    ", ".join(r["flags"]),
                ])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="access-matrix.csv"'
        return resp


class DashboardSummaryView(PlantParamGuardedView):
    def get(self, request):
        return Response(services.dashboard_summary(request.query_params.get("plant")))


class KpiOverviewView(PlantParamGuardedView):
    """
    GET /reporting/kpi-overview/?plant=<uuid>

    KPI di governance GRC: copertura documenti obbligatori, MTTR, completamento
    formazione obbligatoria, copertura NDA fornitori.
    """

    def get(self, request):
        return Response(services.kpi_overview(request.query_params.get("plant")))


# ── KPI suggestion engine (catalogo standard → import) ───────────────────────


class KpiSuggestView(PlantParamGuardedView):
    """
    GET /api/v1/kpi-suggest/?plant=<uuid>&lang=it

    Suggerisce KPI standard dal catalogo in base ai framework attivi del plant.
    Pura lettura: non crea nulla.
    """

    def get(self, request):
        return Response(services.kpi_suggest(
            request.query_params.get("plant"),
            _resolve_lang(request),
        ))


class KpiImportSuggestionsView(APIView):
    """
    POST /api/v1/kpi-suggest/import/

    Importa i KPI suggeriti confermati dall'utente (idempotente).
    """

    permission_classes = [ReportingPermission]

    def post(self, request):
        from apps.plants.models import Plant
        from apps.tasks import services as tasks_services

        kpi_codes = request.data.get("kpi_codes") or []
        if not isinstance(kpi_codes, list) or not kpi_codes:
            return Response(
                {"error": "kpi_codes deve essere una lista non vuota."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plant_id = request.data.get("plant")
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        if plant_id and plant is None:
            return Response(
                {"error": "Plant inesistente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Crea KPI sul plant richiesto (o globali se assente): serve accesso al
        # sito; i KPI globali restano riservati allo scope org (sweep 2026-06-12).
        require_plant_access(request.user, plant)

        overrides = request.data.get("overrides") or {}
        if not isinstance(overrides, dict):
            overrides = {}

        result = tasks_services.import_kpi_suggestions(
            plant=plant,
            kpi_codes=kpi_codes,
            overrides=overrides,
            user=request.user,
        )
        return Response(result, status=status.HTTP_201_CREATED)
