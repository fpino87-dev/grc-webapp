from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q, Avg, ExpressionWrapper, F, DurationField
from django.utils import timezone

from .permissions import ReportingPermission


class ComplianceSummaryView(APIView):
    permission_classes = [ReportingPermission]

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
    permission_classes = [ReportingPermission]

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
    permission_classes = [ReportingPermission]

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
    permission_classes = [ReportingPermission]

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
    permission_classes = [ReportingPermission]

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


class RiskBiaBcpView(APIView):
    """
    Endpoint unificato Risk + BIA + BCP per il tab dedicato nel Reporting.
    GET /reporting/risk-bia-bcp/?plant=<uuid>
    """
    permission_classes = [ReportingPermission]

    def get(self, request):
        from apps.risk.models import (
            RiskAssessment, THREAT_CATEGORIES, NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES
        )
        from apps.bia.models import CriticalProcess
        from apps.bcp.models import BcpPlan, BcpTest

        plant_id = request.query_params.get("plant")
        today = timezone.now().date()

        # ------------------------------------------------------------------ #
        # Base querysets                                                       #
        # ------------------------------------------------------------------ #
        risk_qs = RiskAssessment.objects.filter(
            status="completato", deleted_at__isnull=True
        ).select_related("owner", "accepted_by")
        bia_qs = CriticalProcess.objects.filter(deleted_at__isnull=True)
        bcp_qs = BcpPlan.objects.filter(deleted_at__isnull=True)

        if plant_id:
            risk_qs = risk_qs.filter(plant_id=plant_id)
            bia_qs = bia_qs.filter(plant_id=plant_id)
            bcp_qs = bcp_qs.filter(plant_id=plant_id)

        # ------------------------------------------------------------------ #
        # KPIs                                                                 #
        # ------------------------------------------------------------------ #
        risks_total = risk_qs.count()
        risks_red = risk_qs.filter(score__gt=14).count()
        risks_yellow = risk_qs.filter(score__gt=7, score__lte=14).count()
        risks_needs_revaluation = risk_qs.filter(needs_revaluation=True).count()
        risks_formally_accepted = risk_qs.filter(risk_accepted_formally=True).count()

        # Processi BIA critici (criticality >= 4) senza alcun piano BCP attivo
        critical_proc_ids = set(
            bia_qs.filter(criticality__gte=4).values_list("id", flat=True)
        )
        procs_with_bcp = set(
            bcp_qs.filter(
                critical_process__in=critical_proc_ids, status__in=["approvato", "in_revisione"]
            ).values_list("critical_process_id", flat=True)
        )
        bia_critical_no_bcp = len(critical_proc_ids - procs_with_bcp)

        # BCP con test scaduto (next_test_date passata) o mai testati
        bcp_test_overdue = bcp_qs.filter(
            Q(next_test_date__lt=today) | Q(next_test_date__isnull=True)
        ).count()

        # ------------------------------------------------------------------ #
        # Heatmap 5x5: count rischi per (probability, impact)                 #
        # ------------------------------------------------------------------ #
        heatmap_raw = (
            risk_qs.filter(probability__isnull=False, impact__isnull=False)
            .values("probability", "impact")
            .annotate(count=Count("id"))
        )
        heatmap_dict = {(r["probability"], r["impact"]): r["count"] for r in heatmap_raw}
        heatmap = []
        for prob in range(1, 6):
            for imp in range(1, 6):
                heatmap.append({
                    "prob": prob,
                    "impact": imp,
                    "count": heatmap_dict.get((prob, imp), 0),
                })

        # ------------------------------------------------------------------ #
        # Top 10 rischi per score                                              #
        # ------------------------------------------------------------------ #
        top_risks_qs = (
            risk_qs.filter(score__isnull=False)
            .order_by("-score")[:10]
        )
        threat_label_map = dict(THREAT_CATEGORIES)
        nis2_relevance_label_map = dict(NIS2_RELEVANCE_CHOICES)
        top_risks = []
        for r in top_risks_qs:
            top_risks.append({
                "id": str(r.id),
                "name": r.name,
                "score": r.score,
                "inherent_score": r.inherent_score,
                "threat_category": r.threat_category,
                "threat_label": threat_label_map.get(r.threat_category, r.threat_category),
                "treatment": r.treatment,
                "nis2_relevance": r.nis2_relevance,
                "nis2_relevance_label": nis2_relevance_label_map.get(r.nis2_relevance, ""),
                "nis2_art21_category": r.nis2_art21_category,
                "owner_name": (
                    f"{r.owner.first_name} {r.owner.last_name}".strip()
                    if r.owner else "—"
                ),
                "formally_accepted": r.risk_accepted_formally,
                "needs_revaluation": r.needs_revaluation,
            })

        # ------------------------------------------------------------------ #
        # Breakdown per categoria minaccia (residual avg score vs inherent)   #
        # ------------------------------------------------------------------ #
        by_threat_raw = (
            risk_qs.values("threat_category")
            .annotate(
                count=Count("id"),
                residual_avg=Avg("score"),
                inherent_avg=Avg("inherent_score"),
                rossi=Count("id", filter=Q(score__gt=14)),
                gialli=Count("id", filter=Q(score__gt=7, score__lte=14)),
                verdi=Count("id", filter=Q(score__lte=7)),
            )
            .order_by("-count")
        )
        by_threat = [
            {
                "category": r["threat_category"] or "altro",
                "label": threat_label_map.get(r["threat_category"] or "altro", r["threat_category"] or "Altro"),
                "count": r["count"],
                "residual_avg": round(r["residual_avg"] or 0, 1),
                "inherent_avg": round(r["inherent_avg"] or 0, 1),
                "rossi": r["rossi"],
                "gialli": r["gialli"],
                "verdi": r["verdi"],
            }
            for r in by_threat_raw
        ]

        # ------------------------------------------------------------------ #
        # NIS2 Art.21 breakdown                                               #
        # ------------------------------------------------------------------ #
        nis2_art21_label_map = dict(NIS2_ART21_CHOICES)
        nis2_raw = (
            risk_qs.filter(nis2_art21_category__gt="")
            .values("nis2_art21_category")
            .annotate(
                total=Count("id"),
                significativo=Count("id", filter=Q(nis2_relevance="significativo")),
                potenzialmente=Count("id", filter=Q(nis2_relevance="potenzialmente_significativo")),
                non_significativo=Count("id", filter=Q(nis2_relevance="non_significativo")),
            )
            .order_by("nis2_art21_category")
        )
        nis2_breakdown = [
            {
                "category": r["nis2_art21_category"],
                "label": nis2_art21_label_map.get(r["nis2_art21_category"], r["nis2_art21_category"]),
                "total": r["total"],
                "significativo": r["significativo"],
                "potenzialmente_significativo": r["potenzialmente"],
                "non_significativo": r["non_significativo"],
            }
            for r in nis2_raw
        ]

        # ------------------------------------------------------------------ #
        # Tabella BIA–BCP correlation (tutti i processi)                      #
        # ------------------------------------------------------------------ #
        processes = list(bia_qs.select_related("owner").order_by("-criticality", "name"))

        # Prefetch: rischi per processo
        proc_ids = [p.id for p in processes]
        risk_by_proc = {}
        for r in risk_qs.filter(critical_process_id__in=proc_ids).values(
            "critical_process_id", "score"
        ):
            pid = r["critical_process_id"]
            if pid not in risk_by_proc:
                risk_by_proc[pid] = []
            risk_by_proc[pid].append(r["score"] or 0)

        # Prefetch: BCP piani per processo
        bcp_by_proc = {}
        for bcp in bcp_qs.filter(critical_process__in=proc_ids).values(
            "critical_process_id", "status", "next_test_date", "last_test_date", "id"
        ):
            pid = bcp["critical_process_id"]
            if pid not in bcp_by_proc:
                bcp_by_proc[pid] = []
            bcp_by_proc[pid].append(bcp)

        # Prefetch: ultimo test BCP per piano
        bcp_plan_ids = [
            bcp["id"]
            for bcps in bcp_by_proc.values()
            for bcp in bcps
        ]
        last_test_by_plan = {}
        for test in (
            BcpTest.objects.filter(plan_id__in=bcp_plan_ids, deleted_at__isnull=True)
            .order_by("plan_id", "-test_date")
            .values("plan_id", "test_date", "result")
        ):
            pid = test["plan_id"]
            if pid not in last_test_by_plan:
                last_test_by_plan[pid] = test

        bia_bcp_table = []
        for proc in processes:
            scores = risk_by_proc.get(proc.id, [])
            bcp_plans = bcp_by_proc.get(proc.id, [])

            # Find best BCP (approvato > in_revisione > bozza)
            best_bcp = None
            for priority_status in ("approvato", "in_revisione", "bozza"):
                for b in bcp_plans:
                    if b["status"] == priority_status:
                        best_bcp = b
                        break
                if best_bcp:
                    break

            last_test = None
            if best_bcp:
                last_test = last_test_by_plan.get(best_bcp["id"])

            bia_bcp_table.append({
                "process_id": str(proc.id),
                "process_name": proc.name,
                "criticality": proc.criticality,
                "bia_status": proc.status if hasattr(proc, "status") else "bozza",
                "rto_target_hours": proc.rto_target_hours,
                "rpo_target_hours": proc.rpo_target_hours,
                "risks_total": len(scores),
                "risks_red": sum(1 for s in scores if s > 14),
                "risks_yellow": sum(1 for s in scores if 7 < s <= 14),
                "risks_green": sum(1 for s in scores if s <= 7),
                "bcp_plans_count": len(bcp_plans),
                "bcp_status": best_bcp["status"] if best_bcp else None,
                "next_test_date": (
                    best_bcp["next_test_date"].isoformat() if best_bcp and best_bcp["next_test_date"] else None
                ),
                "last_test_date": (
                    last_test["test_date"].isoformat() if last_test else None
                ),
                "last_test_result": last_test["result"] if last_test else None,
                "test_overdue": (
                    best_bcp["next_test_date"] < today
                    if best_bcp and best_bcp["next_test_date"] else bool(best_bcp)
                ),
            })

        return Response({
            "kpis": {
                "risks_total": risks_total,
                "risks_red": risks_red,
                "risks_yellow": risks_yellow,
                "risks_needs_revaluation": risks_needs_revaluation,
                "risks_formally_accepted": risks_formally_accepted,
                "bia_critical_no_bcp": bia_critical_no_bcp,
                "bcp_test_overdue": bcp_test_overdue,
            },
            "heatmap": heatmap,
            "top_risks": top_risks,
            "by_threat": by_threat,
            "nis2_breakdown": nis2_breakdown,
            "bia_bcp_table": bia_bcp_table,
        })


class DashboardSummaryView(APIView):
    permission_classes = [ReportingPermission]

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

        incidents_open = inc_qs.count()
        pct_compliant = round(compliant / total_ci * 100, 1) if total_ci > 0 else 0

        return Response({
            # Campi flat usati dal frontend ReportingPage
            "plants_active": Plant.objects.filter(deleted_at__isnull=True).count(),
            "controls_total": total_ci,
            "controls_compliant": compliant,
            "controls_gap": gap,
            "pct_compliant": pct_compliant,
            "incidents_open": incidents_open,
            # Campi extra (usati da dashboard e altri moduli)
            "plant_id": plant_id,
            "frameworks": fw_codes,
            "tasks_overdue": task_qs.count(),
            "pdca_open": pdca_qs.count(),
            "risks_red": risk_qs.filter(score__gt=14).count(),
            "risks_yellow": risk_qs.filter(score__gt=7, score__lte=14).count(),
            "incidents_nis2": inc_qs.filter(nis2_notifiable="si").count(),
            "vacant_roles": get_vacant_mandatory_roles(plant) if plant else [],
        })


class KpiOverviewView(APIView):
    """
    GET /reporting/kpi-overview/?plant=<uuid>

    Restituisce i KPI di governance GRC:
    - required_docs: copertura documenti obbligatori per framework attivo
    - mttr: tempo medio di risoluzione (finding audit, incidenti, task)
    - training: completamento formazione obbligatoria (perimetro utenti GRC)
    """
    permission_classes = [ReportingPermission]

    def get(self, request):
        plant_id = request.query_params.get("plant")
        plant = None
        if plant_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()

        return Response({
            "required_docs": self._required_docs(plant),
            "mttr": self._mttr(plant_id),
            "training": self._training(plant),
            "supplier_nda": self._supplier_nda(plant),
        })

    # ------------------------------------------------------------------ #
    # 1. Required documents coverage                                       #
    # ------------------------------------------------------------------ #
    def _required_docs(self, plant):
        from apps.compliance_schedule.services import get_required_documents_status
        from apps.plants.services import get_active_framework_codes

        ALL_FRAMEWORKS = ["ISO27001", "NIS2", "ACN_NIS2", "TISAX_L2", "TISAX_L3"]

        if plant:
            frameworks = get_active_framework_codes(plant)
        else:
            frameworks = ALL_FRAMEWORKS

        result = []
        for fw in frameworks:
            items = get_required_documents_status(plant=plant, framework=fw)
            total = len(items)
            if total == 0:
                # Nessun RequiredDocument configurato: mostra la copertura dei controlli
                from apps.controls.models import ControlInstance
                ci_qs = ControlInstance.objects.filter(
                    control__framework__code=fw,
                    deleted_at__isnull=True,
                )
                if plant:
                    ci_qs = ci_qs.filter(plant=plant)
                ci_total = ci_qs.count()
                ci_compliant = ci_qs.filter(status="compliant").count()
                ci_gap = ci_qs.filter(status="gap").count()
                ci_other = ci_total - ci_compliant - ci_gap
                result.append({
                    "framework": fw,
                    "total": ci_total,
                    "green": ci_compliant,
                    "yellow": ci_other,
                    "red": ci_gap,
                    "pct_coverage": round(ci_compliant / ci_total * 100, 1) if ci_total else 0,
                    "mandatory_total": 0,
                    "mandatory_ok": 0,
                    "pct_mandatory": 0,
                    "no_required_docs": True,
                })
                continue
            green = sum(1 for i in items if i["traffic_light"] == "green")
            yellow = sum(1 for i in items if i["traffic_light"] == "yellow")
            red = sum(1 for i in items if i["traffic_light"] == "red")
            mandatory_total = sum(1 for i in items if i["mandatory"])
            mandatory_ok = sum(1 for i in items if i["mandatory"] and i["traffic_light"] == "green")
            result.append({
                "framework": fw,
                "total": total,
                "green": green,
                "yellow": yellow,
                "red": red,
                "pct_coverage": round(green / total * 100, 1) if total else 0,
                "mandatory_total": mandatory_total,
                "mandatory_ok": mandatory_ok,
                "pct_mandatory": round(mandatory_ok / mandatory_total * 100, 1) if mandatory_total else 0,
                "no_required_docs": False,
            })
        return result

    # ------------------------------------------------------------------ #
    # 2. Mean Time To Remediate                                            #
    # ------------------------------------------------------------------ #
    def _mttr(self, plant_id):
        from apps.audit_prep.models import AuditFinding
        from apps.incidents.models import Incident
        from apps.tasks.models import Task

        duration_expr = ExpressionWrapper(
            F("closed_at") - F("created_at"),
            output_field=DurationField(),
        )
        task_duration_expr = ExpressionWrapper(
            F("completed_at") - F("created_at"),
            output_field=DurationField(),
        )

        def td_to_days(td):
            if td is None:
                return None
            return round(td.total_seconds() / 86400, 1)

        # --- Findings ---
        f_base = AuditFinding.objects.filter(
            closed_at__isnull=False,
            deleted_at__isnull=True,
        )
        if plant_id:
            f_base = f_base.filter(audit_prep__plant_id=plant_id)

        findings = {}
        for ftype in ("major", "minor", "observation"):
            agg = f_base.filter(finding_type=ftype).annotate(dur=duration_expr).aggregate(
                count=Count("id"), avg=Avg("dur")
            )
            findings[ftype] = {
                "count": agg["count"],
                "avg_days": td_to_days(agg["avg"]),
            }
        findings["all"] = {
            "count": f_base.count(),
            "avg_days": td_to_days(
                f_base.annotate(dur=duration_expr).aggregate(avg=Avg("dur"))["avg"]
            ),
        }

        # --- Incidents ---
        i_base = Incident.objects.filter(
            closed_at__isnull=False,
            deleted_at__isnull=True,
        )
        if plant_id:
            i_base = i_base.filter(plant_id=plant_id)

        incidents_all = i_base.annotate(dur=duration_expr).aggregate(
            count=Count("id"), avg=Avg("dur")
        )
        incidents_by_sev = {}
        for sev in ("critica", "alta", "media", "bassa"):
            agg = i_base.filter(severity=sev).annotate(dur=duration_expr).aggregate(
                count=Count("id"), avg=Avg("dur")
            )
            if agg["count"]:
                incidents_by_sev[sev] = {
                    "count": agg["count"],
                    "avg_days": td_to_days(agg["avg"]),
                }

        # --- Tasks ---
        t_base = Task.objects.filter(
            status="completato",
            completed_at__isnull=False,
            deleted_at__isnull=True,
        )
        if plant_id:
            t_base = t_base.filter(plant_id=plant_id)

        tasks_all = t_base.annotate(dur=task_duration_expr).aggregate(
            count=Count("id"), avg=Avg("dur")
        )

        return {
            "findings": findings,
            "incidents": {
                "all": {
                    "count": incidents_all["count"],
                    "avg_days": td_to_days(incidents_all["avg"]),
                },
                "by_severity": incidents_by_sev,
            },
            "tasks": {
                "all": {
                    "count": tasks_all["count"],
                    "avg_days": td_to_days(tasks_all["avg"]),
                },
            },
        }

    # ------------------------------------------------------------------ #
    # 3. Training completion (GRC users perimeter)                        #
    # ------------------------------------------------------------------ #
    def _training(self, plant):
        from apps.training.models import TrainingCourse, TrainingEnrollment
        from apps.auth_grc.models import UserPlantAccess
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Perimetro: utenti attivi con almeno un accesso GRC non eliminato.
        # scope_plants vuoto = accesso a tutti i plant; scope_plants pieno = accesso limitato.
        if plant:
            accessible_ids = (
                UserPlantAccess.objects.filter(deleted_at__isnull=True)
                .filter(Q(scope_plants=plant) | Q(scope_plants__isnull=True))
                .values_list("user_id", flat=True)
            )
            user_qs = User.objects.filter(id__in=accessible_ids, is_active=True).distinct()
        else:
            user_qs = User.objects.filter(
                plant_access__deleted_at__isnull=True,
                is_active=True,
            ).distinct()

        total_users = user_qs.count()
        user_ids = list(user_qs.values_list("id", flat=True))

        # Corsi obbligatori attivi
        course_qs = TrainingCourse.objects.filter(mandatory=True, status="attivo")
        if plant:
            course_qs = course_qs.filter(plants=plant)

        mandatory_courses = []
        mandatory_course_ids = list(course_qs.values_list("id", flat=True))

        for course in course_qs.order_by("title"):
            enrolled = TrainingEnrollment.objects.filter(
                course=course, user_id__in=user_ids
            ).count()
            completed = TrainingEnrollment.objects.filter(
                course=course, user_id__in=user_ids, status="completato"
            ).count()
            mandatory_courses.append({
                "id": str(course.id),
                "title": course.title,
                "source": course.source,
                "deadline": str(course.deadline) if course.deadline else None,
                "enrolled": enrolled,
                "completed": completed,
                "pct_completed": round(completed / enrolled * 100, 1) if enrolled else 0,
                "not_enrolled": total_users - enrolled,
            })

        # Utenti che hanno completato TUTTI i corsi obbligatori
        if mandatory_course_ids and user_ids:
            users_all_done = 0
            for uid in user_ids:
                completed_count = TrainingEnrollment.objects.filter(
                    user_id=uid,
                    course_id__in=mandatory_course_ids,
                    status="completato",
                ).values("course_id").distinct().count()
                if completed_count >= len(mandatory_course_ids):
                    users_all_done += 1
        else:
            users_all_done = 0

        return {
            "total_users": total_users,
            "mandatory_courses_count": len(mandatory_course_ids),
            "users_all_mandatory_completed": users_all_done,
            "pct_all_mandatory": round(users_all_done / total_users * 100, 1) if total_users else 0,
            "courses": mandatory_courses,
        }

    # ------------------------------------------------------------------ #
    # 4. Supplier NDA coverage                                            #
    # ------------------------------------------------------------------ #
    def _supplier_nda(self, plant):
        from apps.suppliers.models import Supplier
        from apps.documents.models import Document
        from django.utils import timezone

        today = timezone.now().date()
        threshold_90 = today + timezone.timedelta(days=90)

        supplier_qs = Supplier.objects.filter(status="attivo", deleted_at__isnull=True)
        if plant:
            # include fornitori esplicitamente associati al plant + quelli globali (plants=[])
            supplier_qs = supplier_qs.filter(
                Q(plants=plant) | Q(plants__isnull=True)
            ).distinct()

        total = supplier_qs.count()

        # Fornitori con almeno un NDA approvato
        with_approved = supplier_qs.filter(
            nda_documents__document_type="contratto",
            nda_documents__status="approvato",
            nda_documents__deleted_at__isnull=True,
        ).distinct().count()

        # Fornitori con NDA approvato ma in scadenza entro 90 giorni
        expiring = supplier_qs.filter(
            nda_documents__document_type="contratto",
            nda_documents__status="approvato",
            nda_documents__deleted_at__isnull=True,
            nda_documents__expiry_date__lte=threshold_90,
            nda_documents__expiry_date__gte=today,
        ).distinct().count()

        # Fornitori con NDA scaduto
        expired = supplier_qs.filter(
            nda_documents__document_type="contratto",
            nda_documents__status="approvato",
            nda_documents__deleted_at__isnull=True,
            nda_documents__expiry_date__lt=today,
        ).distinct().count()

        without_nda = total - supplier_qs.filter(
            nda_documents__document_type="contratto",
            nda_documents__deleted_at__isnull=True,
        ).distinct().count()

        # Tabella per KPI: tutti i fornitori con stato NDA
        suppliers_detail = []
        for s in supplier_qs.prefetch_related("nda_documents").order_by("name"):
            ndas = [
                d for d in s.nda_documents.all()
                if d.document_type == "contratto" and d.deleted_at is None
            ]
            approved_ndas = [d for d in ndas if d.status == "approvato"]
            latest = approved_ndas[0] if approved_ndas else (ndas[0] if ndas else None)

            if not ndas:
                nda_status = "missing"
            elif approved_ndas:
                if latest.expiry_date and latest.expiry_date < today:
                    nda_status = "expired"
                elif latest.expiry_date and latest.expiry_date <= threshold_90:
                    nda_status = "expiring"
                else:
                    nda_status = "ok"
            else:
                nda_status = "draft"

            expiry_date = latest.expiry_date if latest else None
            if expiry_date:
                days_to_expiry = (expiry_date - today).days
            else:
                days_to_expiry = None

            suppliers_detail.append({
                "id": str(s.id),
                "name": s.name,
                "risk_level": s.risk_level,
                "nda_status": nda_status,
                "expiry_date": str(expiry_date) if expiry_date else None,
                "days_to_expiry": days_to_expiry,
            })

        return {
            "total": total,
            "covered": with_approved,
            "expiring_soon": expiring,
            "expired": expired,
            "without_nda": without_nda,
            "suppliers": suppliers_detail,
        }
