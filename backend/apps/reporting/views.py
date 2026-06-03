from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .permissions import ReportingPermission


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


class ComplianceSummaryView(APIView):
    """
    GET /api/v1/reporting/compliance/?plant=<uuid>&framework=<code>

    Riusa `apps.controls.services.get_compliance_summary` per garantire
    coerenza con la dashboard e con il GRC Assistant.
    """

    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.compliance_summary(
            request.query_params.get("plant"),
            request.query_params.get("framework"),
        ))


class RiskSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.risk_summary(request.query_params.get("plant")))


class IncidentSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.incident_summary(request.query_params.get("plant")))


class OwnerReportView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.owner_report(request.query_params.get("plant")))


class KpiTrendView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.kpi_trend(
            request.query_params.get("plant"),
            request.query_params.get("framework", "ISO27001"),
            request.query_params.get("weeks", 12),
        ))


class RiskBiaBcpView(APIView):
    """
    Endpoint unificato Risk + BIA + BCP per il tab dedicato nel Reporting.
    GET /reporting/risk-bia-bcp/?plant=<uuid>
    """
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.risk_bia_bcp(request.query_params.get("plant")))


class DashboardSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.dashboard_summary(request.query_params.get("plant")))


class KpiOverviewView(APIView):
    """
    GET /reporting/kpi-overview/?plant=<uuid>

    KPI di governance GRC: copertura documenti obbligatori, MTTR, completamento
    formazione obbligatoria, copertura NDA fornitori.
    """
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(services.kpi_overview(request.query_params.get("plant")))


# ── KPI suggestion engine (catalogo standard → import) ───────────────────────


class KpiSuggestView(APIView):
    """
    GET /api/v1/kpi-suggest/?plant=<uuid>&lang=it

    Suggerisce KPI standard dal catalogo in base ai framework attivi del plant.
    Pura lettura: non crea nulla.
    """

    permission_classes = [ReportingPermission]

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
