from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.scoping import require_plant_access

from . import services
from .permissions import ReportingPermission


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
