from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q


class ComplianceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.controls.models import ControlInstance
        plant_id = request.query_params.get("plant")
        framework_code = request.query_params.get("framework")
        qs = ControlInstance.objects.all()
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        if framework_code:
            qs = qs.filter(control__framework__code=framework_code)
        totals = qs.values("status").annotate(n=Count("id"))
        total = qs.count()
        by_status = {r["status"]: r["n"] for r in totals}
        compliant = by_status.get("compliant", 0)
        return Response({
            "total": total,
            "by_status": by_status,
            "pct_compliant": round(compliant / total * 100, 1) if total else 0,
        })


class RiskSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.risk.models import RiskAssessment
        plant_id = request.query_params.get("plant")
        qs = RiskAssessment.objects.filter(status="completato")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        high = qs.filter(score__gt=14).count()
        medium = qs.filter(score__gt=7, score__lte=14).count()
        low = qs.filter(score__lte=7).count()
        return Response({"high": high, "medium": medium, "low": low, "total": qs.count()})


class IncidentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.incidents.models import Incident
        plant_id = request.query_params.get("plant")
        qs = Incident.objects.all()
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        by_severity = dict(qs.values("severity").annotate(n=Count("id")).values_list("severity", "n"))
        by_status = dict(qs.values("status").annotate(n=Count("id")).values_list("status", "n"))
        return Response({"total": qs.count(), "by_severity": by_severity, "by_status": by_status})


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.controls.models import ControlInstance
        from apps.incidents.models import Incident
        from apps.plants.models import Plant
        plant_id = request.query_params.get("plant")

        plants_qs = Plant.objects.filter(status="attivo")
        incidents_open = Incident.objects.filter(status__in=["aperto", "in_analisi"])
        controls_qs = ControlInstance.objects.all()

        if plant_id:
            incidents_open = incidents_open.filter(plant_id=plant_id)
            controls_qs = controls_qs.filter(plant_id=plant_id)

        total_controls = controls_qs.count()
        compliant = controls_qs.filter(status="compliant").count()

        return Response({
            "plants_active": plants_qs.count(),
            "incidents_open": incidents_open.count(),
            "controls_total": total_controls,
            "controls_compliant": compliant,
            "controls_gap": controls_qs.filter(status="gap").count(),
            "pct_compliant": round(compliant / total_controls * 100, 1) if total_controls else 0,
        })
