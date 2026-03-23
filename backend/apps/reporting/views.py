from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone


class ComplianceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.controls.models import ControlInstance
        plant_id = request.query_params.get("plant")
        framework_code = request.query_params.get("framework")
        qs = ControlInstance.objects.all()
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
            if not framework_code:
                from apps.plants.services import get_active_frameworks
                from apps.plants.models import Plant
                plant = Plant.objects.filter(pk=plant_id).first()
                if plant:
                    qs = qs.filter(control__framework__in=get_active_frameworks(plant))
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


class OwnerReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.risk.models import RiskAssessment
        from apps.bia.models import CriticalProcess
        from apps.tasks.models import Task

        plant_id = request.query_params.get("plant")

        risks_qs = RiskAssessment.objects.filter(
            status="completato", deleted_at__isnull=True
        )
        if plant_id:
            risks_qs = risks_qs.filter(plant_id=plant_id)

        risks_by_owner = list(
            risks_qs.values(
                "owner__id", "owner__first_name", "owner__last_name", "owner__email"
            ).annotate(
                totale=Count("id"),
                rossi=Count("id", filter=Q(score__gt=14)),
                gialli=Count("id", filter=Q(score__gt=7, score__lte=14)),
                verdi=Count("id", filter=Q(score__lte=7)),
            ).order_by("-rossi")
        )

        # Add process count per owner
        for entry in risks_by_owner:
            owner_id = entry["owner__id"]
            procs_qs = CriticalProcess.objects.filter(deleted_at__isnull=True)
            if plant_id:
                procs_qs = procs_qs.filter(plant_id=plant_id)
            if owner_id:
                entry["processes"] = procs_qs.filter(owner_id=owner_id).count()
            else:
                entry["processes"] = 0
            entry["owner_name"] = f"{entry['owner__first_name']} {entry['owner__last_name']}".strip() or entry.get("owner__email") or "—"
            entry["owner_email"] = entry["owner__email"] or ""

        # Tasks by owner
        since_30 = timezone.now() - timezone.timedelta(days=30)
        tasks_qs = Task.objects.filter(deleted_at__isnull=True)
        if plant_id:
            tasks_qs = tasks_qs.filter(plant_id=plant_id)

        tasks_by_owner = list(
            tasks_qs.values(
                "assigned_to__first_name", "assigned_to__last_name", "assigned_to__email"
            ).annotate(
                aperti=Count("id", filter=Q(status__in=["aperto", "in_corso"])),
                scaduti=Count("id", filter=Q(
                    status__in=["aperto", "in_corso"],
                    due_date__lt=timezone.now().date(),
                )),
                completati_30gg=Count("id", filter=Q(
                    status="completato",
                    completed_at__gte=since_30,
                )),
            ).order_by("-aperti")
        )
        for entry in tasks_by_owner:
            entry["owner_name"] = (
                f"{entry['assigned_to__first_name']} {entry['assigned_to__last_name']}".strip()
                or entry.get("assigned_to__email") or "—"
            )

        return Response({
            "risks_by_owner": risks_by_owner,
            "tasks_by_owner": tasks_by_owner,
        })


class KpiTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import IsmsKpiSnapshot
        plant_id = request.query_params.get("plant")
        framework_code = request.query_params.get("framework", "ISO27001")
        try:
            weeks = int(request.query_params.get("weeks", 12))
        except ValueError:
            weeks = 12
        weeks = min(max(weeks, 1), 52)

        qs = IsmsKpiSnapshot.objects.filter(framework_code=framework_code)
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        else:
            qs = qs.filter(plant__isnull=True)
        qs = qs.order_by("week_start")[:weeks]

        data = list(qs.values(
            "week_start", "pct_compliant", "overall_maturity",
            "open_risks", "high_risks", "open_incidents", "critical_incidents",
            "controls_compliant", "controls_total", "controls_gap",
        ))
        return Response({"results": data, "framework": framework_code})


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.controls.models import ControlInstance
        from apps.incidents.models import Incident
        from apps.plants.models import Plant
        from apps.plants.services import get_active_framework_codes
        from apps.risk.models import RiskAssessment
        from apps.tasks.models import Task
        from apps.pdca.models import PdcaCycle
        from apps.governance.services import get_vacant_mandatory_roles

        plant_id = request.query_params.get("plant")
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        today = timezone.now().date()
        fw_codes = get_active_framework_codes(plant) if plant else []

        ci_qs = ControlInstance.objects.filter(deleted_at__isnull=True)
        if plant:
            ci_qs = ci_qs.filter(
                plant=plant,
                control__framework__code__in=fw_codes,
            )
        total_ci = ci_qs.count()
        compliant = ci_qs.filter(status="compliant").count()
        gap = ci_qs.filter(status="gap").count()

        risk_qs = RiskAssessment.objects.filter(
            status="completato", deleted_at__isnull=True
        )
        if plant:
            risk_qs = risk_qs.filter(plant=plant)

        inc_qs = Incident.objects.filter(status__in=["aperto", "in_analisi"])
        if plant:
            inc_qs = inc_qs.filter(plant=plant)

        task_qs = Task.objects.filter(
            status__in=["aperto", "in_corso"],
            due_date__lt=today,
        )
        if plant:
            task_qs = task_qs.filter(plant=plant)

        pdca_qs = PdcaCycle.objects.exclude(fase_corrente="chiuso")
        if plant:
            pdca_qs = pdca_qs.filter(plant=plant)

        return Response({
            "plant_id": plant_id,
            "frameworks": fw_codes,
            "compliance": {
                "total": total_ci,
                "compliant": compliant,
                "gap": gap,
                "pct": round(compliant / total_ci * 100, 1) if total_ci > 0 else 0,
            },
            "risks": {
                "red": risk_qs.filter(score__gt=14).count(),
                "yellow": risk_qs.filter(score__gt=7, score__lte=14).count(),
            },
            "incidents": {
                "open": inc_qs.count(),
                "nis2": inc_qs.filter(nis2_notifiable="si").count(),
            },
            "tasks_overdue": task_qs.count(),
            "pdca_open": pdca_qs.count(),
            "vacant_roles": get_vacant_mandatory_roles(plant) if plant else [],
        })
