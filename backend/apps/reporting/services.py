"""
Logica di reporting (M18) — funzioni pure, testabili indipendentemente dalle view.

Ogni funzione prende parametri primitivi (plant_id stringa/UUID o None, codici
framework, ecc.) e restituisce strutture dati semplici (dict/list) pronte per la
serializzazione. Nessun oggetto Request/Response qui (regola architetturale #2:
business logic in services, non nelle view).

Gli import dei modelli sono volutamente locali alle funzioni per evitare cicli di
import tra app e mantenere leggero il caricamento del modulo.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone


# ───────────────────────────────────────────────────────────────────────────
# Compliance summary
# ───────────────────────────────────────────────────────────────────────────
def compliance_summary(plant_id, framework_code=None) -> dict:
    """
    Riusa `apps.controls.services.get_compliance_summary` per coerenza con la
    dashboard e il govrico Assistant (N/A esclusi dal denominatore, extender contati
    come compliant). Senza plant restituisce un sommario vuoto.
    """
    if not plant_id:
        return {"total": 0, "by_status": {}, "pct_compliant": 0}

    from apps.controls.services import get_compliance_summary

    summary = get_compliance_summary(plant_id, framework_code or None)
    # Mantiene la chiave legacy `by_status` per i consumatori esistenti.
    by_status = {
        "compliant": summary["compliant_direct"],
        "gap": summary["gap"],
        "parziale": summary["parziale"],
        "non_valutato": summary["non_valutato"],
        "na": summary["na_excluded"],
    }
    return {**summary, "by_status": by_status}


# ───────────────────────────────────────────────────────────────────────────
# Risk summary
# ───────────────────────────────────────────────────────────────────────────
def risk_summary(plant_id) -> dict:
    from apps.risk.models import RiskAssessment

    qs = RiskAssessment.objects.filter(status="completato")
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    high = qs.filter(score__gt=14).count()
    medium = qs.filter(score__gt=7, score__lte=14).count()
    low = qs.filter(score__lte=7).count()
    return {"high": high, "medium": medium, "low": low, "total": qs.count()}


# ───────────────────────────────────────────────────────────────────────────
# Incident summary
# ───────────────────────────────────────────────────────────────────────────
def incident_summary(plant_id) -> dict:
    from apps.incidents.models import Incident

    qs = Incident.objects.all()
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    by_severity = dict(qs.values("severity").annotate(n=Count("id")).values_list("severity", "n"))
    by_status = dict(qs.values("status").annotate(n=Count("id")).values_list("status", "n"))
    return {"total": qs.count(), "by_severity": by_severity, "by_status": by_status}


# ───────────────────────────────────────────────────────────────────────────
# Owner report (rischi e task per responsabile)
# ───────────────────────────────────────────────────────────────────────────
def owner_report(plant_id) -> dict:
    from apps.bia.models import CriticalProcess
    from apps.risk.models import RiskAssessment
    from apps.tasks.models import Task

    risks_qs = RiskAssessment.objects.filter(status="completato", deleted_at__isnull=True)
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

    for entry in risks_by_owner:
        owner_id = entry["owner__id"]
        procs_qs = CriticalProcess.objects.filter(deleted_at__isnull=True)
        if plant_id:
            procs_qs = procs_qs.filter(plant_id=plant_id)
        if owner_id:
            entry["processes"] = procs_qs.filter(owner_id=owner_id).count()
        else:
            entry["processes"] = 0
        entry["owner_name"] = (
            f"{entry['owner__first_name']} {entry['owner__last_name']}".strip()
            or entry.get("owner__email") or "—"
        )
        entry["owner_email"] = entry["owner__email"] or ""

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
                due_date__lt=timezone.localdate(),
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

    return {"risks_by_owner": risks_by_owner, "tasks_by_owner": tasks_by_owner}


# ───────────────────────────────────────────────────────────────────────────
# KPI trend (snapshot ISMS settimanali)
# ───────────────────────────────────────────────────────────────────────────
def kpi_trend(plant_id, framework_code="ISO27001", weeks=12) -> dict:
    from .models import IsmsKpiSnapshot

    try:
        weeks = int(weeks)
    except (TypeError, ValueError):
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
    return {"results": data, "framework": framework_code}


# ───────────────────────────────────────────────────────────────────────────
# Risk + BIA + BCP (vista unificata)
# ───────────────────────────────────────────────────────────────────────────
def risk_bia_bcp(plant_id) -> dict:
    from apps.bcp.models import BcpPlan, BcpTest
    from apps.bia.models import CriticalProcess, TreatmentOption
    from apps.risk.models import (
        NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES, RiskAssessment, THREAT_CATEGORIES,
    )
    from apps.risk.services import calc_ale

    today = timezone.localdate()

    risk_qs = RiskAssessment.objects.filter(
        status="completato", deleted_at__isnull=True
    ).select_related("owner", "accepted_by", "critical_process")
    bia_qs = CriticalProcess.objects.filter(deleted_at__isnull=True)
    bcp_qs = BcpPlan.objects.filter(deleted_at__isnull=True)

    if plant_id:
        risk_qs = risk_qs.filter(plant_id=plant_id)
        bia_qs = bia_qs.filter(plant_id=plant_id)
        bcp_qs = bcp_qs.filter(plant_id=plant_id)

    # KPIs
    risks_total = risk_qs.count()
    risks_red = risk_qs.filter(score__gt=14).count()
    risks_yellow = risk_qs.filter(score__gt=7, score__lte=14).count()
    risks_needs_revaluation = risk_qs.filter(needs_revaluation=True).count()
    risks_formally_accepted = risk_qs.filter(risk_accepted_formally=True).count()

    # ALE (Annualized Loss Expectancy) — perdita attesa annua in €.
    # Calcolata live da calc_ale() sui dati BIA collegati; vale 0 se il rischio
    # non ha processo critico/costo di fermo. residua = post-controlli (campi
    # correnti), inerente = pre-controlli (campi inherent_*). La differenza
    # (inerente − residua) è il rischio già abbattuto dai controlli, in €.
    # critical_process è in select_related → nessuna query N+1; risk_qs viene
    # valutato una sola volta e riusato (cache queryset) per entrambe le ALE.
    ale_by_risk = {}
    ale_inherent_by_risk = {}
    ale_by_proc = {}  # ALE residua aggregata per processo critico → base ROSI
    for r in risk_qs:
        residual = calc_ale(r)
        ale_by_risk[r.id] = residual
        ale_inherent_by_risk[r.id] = calc_ale(r, inherent=True)
        if r.critical_process_id and residual:
            ale_by_proc[r.critical_process_id] = (
                ale_by_proc.get(r.critical_process_id, Decimal("0")) + residual
            )
    ale_total = sum((v for v in ale_by_risk.values() if v), Decimal("0"))
    ale_total_inherent = sum((v for v in ale_inherent_by_risk.values() if v), Decimal("0"))
    ale_saved = ale_total_inherent - ale_total
    ale_valued_count = sum(1 for v in ale_by_risk.values() if v and v > 0)
    ale_coverage_pct = (
        round(ale_valued_count / risks_total * 100, 1) if risks_total else 0.0
    )
    ale_saved_pct = (
        round(float(ale_saved) / float(ale_total_inherent) * 100, 1)
        if ale_total_inherent else 0.0
    )

    critical_proc_ids = set(bia_qs.filter(criticality__gte=4).values_list("id", flat=True))
    procs_with_bcp = set(
        bcp_qs.filter(
            critical_process__in=critical_proc_ids, status__in=["approvato", "in_revisione"]
        ).values_list("critical_process_id", flat=True)
    )
    bia_critical_no_bcp = len(critical_proc_ids - procs_with_bcp)

    bcp_test_overdue = bcp_qs.filter(
        Q(next_test_date__lt=today) | Q(next_test_date__isnull=True)
    ).count()

    # Heatmap 5x5
    heatmap_raw = (
        risk_qs.filter(probability__isnull=False, impact__isnull=False)
        .values("probability", "impact")
        .annotate(count=Count("id"))
    )
    heatmap_dict = {(r["probability"], r["impact"]): r["count"] for r in heatmap_raw}
    heatmap = []
    for prob in range(1, 6):
        for imp in range(1, 6):
            heatmap.append({"prob": prob, "impact": imp, "count": heatmap_dict.get((prob, imp), 0)})

    # Top 10 rischi per score
    top_risks_qs = risk_qs.filter(score__isnull=False).order_by("-score")[:10]
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
                f"{r.owner.first_name} {r.owner.last_name}".strip() if r.owner else "—"
            ),
            "formally_accepted": r.risk_accepted_formally,
            "needs_revaluation": r.needs_revaluation,
            "ale": float(ale_by_risk.get(r.id) or 0),
            "ale_inherent": float(ale_inherent_by_risk.get(r.id) or 0),
        })

    # Breakdown per categoria minaccia
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

    # NIS2 Art.21 breakdown
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

    # Tabella BIA–BCP correlation
    processes = list(bia_qs.select_related("owner").order_by("-criticality", "name"))
    proc_ids = [p.id for p in processes]

    risk_by_proc = {}
    for r in risk_qs.filter(critical_process_id__in=proc_ids).values("critical_process_id", "score"):
        risk_by_proc.setdefault(r["critical_process_id"], []).append(r["score"] or 0)

    bcp_by_proc = {}
    for bcp in bcp_qs.filter(critical_process__in=proc_ids).values(
        "critical_process_id", "status", "next_test_date", "last_test_date", "id"
    ):
        bcp_by_proc.setdefault(bcp["critical_process_id"], []).append(bcp)

    bcp_plan_ids = [bcp["id"] for bcps in bcp_by_proc.values() for bcp in bcps]
    last_test_by_plan = {}
    for test in (
        BcpTest.objects.filter(plan_id__in=bcp_plan_ids, deleted_at__isnull=True)
        .order_by("plan_id", "-test_date")
        .values("plan_id", "test_date", "result")
    ):
        last_test_by_plan.setdefault(test["plan_id"], test)

    bia_bcp_table = []
    for proc in processes:
        scores = risk_by_proc.get(proc.id, [])
        bcp_plans = bcp_by_proc.get(proc.id, [])

        # Best BCP: approvato > in_revisione > bozza; a parità, quello con dati di
        # test più informativi (last_test_date più recente, poi next_test_date).
        best_bcp = None
        for priority_status in ("approvato", "in_revisione", "bozza"):
            candidates = [b for b in bcp_plans if b["status"] == priority_status]
            if candidates:
                candidates.sort(
                    key=lambda b: (
                        b["last_test_date"] is not None,
                        b["last_test_date"] or date.min,
                        b["next_test_date"] is not None,
                        b["next_test_date"] or date.min,
                    ),
                    reverse=True,
                )
                best_bcp = candidates[0]
                break

        last_test = last_test_by_plan.get(best_bcp["id"]) if best_bcp else None

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
            "last_test_date": last_test["test_date"].isoformat() if last_test else None,
            "last_test_result": last_test["result"] if last_test else None,
            "test_overdue": (
                best_bcp["next_test_date"] < today
                if best_bcp and best_bcp["next_test_date"] else bool(best_bcp)
            ),
        })

    # ROSI (Return on Security Investment) dei trattamenti pianificati (M05 BIA).
    # Standard ENISA: ROSI = (ALE_evitata − costo_annualizzato) / costo_annualizzato.
    # Il CapEx una tantum (cost_implementation) è ammortizzato su AMORT_YEARS anni
    # (vita utile convenzionale del controllo); cost_annual è il ricorrente.
    # ALE_evitata = ALE residua del processo × % di riduzione del trattamento.
    # Ogni trattamento è valutato indipendentemente (non sommabile linearmente sullo
    # stesso processo) come supporto alla decisione di investimento.
    AMORT_YEARS = 3
    opt_qs = TreatmentOption.objects.filter(deleted_at__isnull=True).select_related("process")
    if plant_id:
        opt_qs = opt_qs.filter(process__plant_id=plant_id)

    treatments = []
    tot_ale_avoided = Decimal("0")
    tot_annual_cost = Decimal("0")
    for opt in opt_qs:
        proc_ale = ale_by_proc.get(opt.process_id, Decimal("0"))
        reduction = Decimal(str(opt.ale_reduction_pct)) / Decimal("100")
        ale_avoided = (proc_ale * reduction).quantize(Decimal("0.01"))
        annual_cost = (
            Decimal(str(opt.cost_annual))
            + Decimal(str(opt.cost_implementation)) / Decimal(AMORT_YEARS)
        ).quantize(Decimal("0.01"))
        net_annual = ale_avoided - annual_cost
        rosi_pct = (
            round(float(net_annual / annual_cost * 100), 1) if annual_cost > 0 else None
        )
        # payback (mesi): solo CapEx contro il beneficio netto ricorrente positivo
        net_recurring = ale_avoided - Decimal(str(opt.cost_annual))
        payback_months = (
            round(float(Decimal(str(opt.cost_implementation)) / net_recurring * 12), 1)
            if net_recurring > 0 and opt.cost_implementation else None
        )
        worth_it = (rosi_pct is not None and rosi_pct > 0) or (
            annual_cost == 0 and ale_avoided > 0
        )
        treatments.append({
            "id": str(opt.id),
            "title": opt.title,
            "process_id": str(opt.process_id),
            "process_name": opt.process.name,
            "ale_reduction_pct": opt.ale_reduction_pct,
            "process_ale": float(proc_ale),
            "ale_avoided": float(ale_avoided),
            "cost_implementation": float(opt.cost_implementation),
            "cost_annual": float(opt.cost_annual),
            "annual_cost": float(annual_cost),
            "net_annual": float(net_annual),
            "rosi_pct": rosi_pct,
            "payback_months": payback_months,
            "worth_it": worth_it,
        })
        tot_ale_avoided += ale_avoided
        tot_annual_cost += annual_cost

    # Ordina per ROSI decrescente (i None — costo annuo nullo — in coda)
    treatments.sort(
        key=lambda x: (x["rosi_pct"] is not None, x["rosi_pct"] if x["rosi_pct"] is not None else -1e9),
        reverse=True,
    )
    treatments_totals = {
        "count": len(treatments),
        "ale_avoided": float(tot_ale_avoided),
        "annual_cost": float(tot_annual_cost),
        "net_annual": float(tot_ale_avoided - tot_annual_cost),
        "rosi_pct": (
            round(float((tot_ale_avoided - tot_annual_cost) / tot_annual_cost * 100), 1)
            if tot_annual_cost > 0 else None
        ),
        "amort_years": AMORT_YEARS,
    }

    return {
        "kpis": {
            "risks_total": risks_total,
            "risks_red": risks_red,
            "risks_yellow": risks_yellow,
            "risks_needs_revaluation": risks_needs_revaluation,
            "risks_formally_accepted": risks_formally_accepted,
            "bia_critical_no_bcp": bia_critical_no_bcp,
            "bcp_test_overdue": bcp_test_overdue,
            "ale_total": float(ale_total),
            "ale_total_inherent": float(ale_total_inherent),
            "ale_saved": float(ale_saved),
            "ale_saved_pct": ale_saved_pct,
            "ale_valued_count": ale_valued_count,
            "ale_coverage_pct": ale_coverage_pct,
        },
        "heatmap": heatmap,
        "top_risks": top_risks,
        "by_threat": by_threat,
        "nis2_breakdown": nis2_breakdown,
        "bia_bcp_table": bia_bcp_table,
        "treatments": treatments,
        "treatments_totals": treatments_totals,
    }


# ───────────────────────────────────────────────────────────────────────────
# Dashboard summary (KPI flat per la ReportingPage)
# ───────────────────────────────────────────────────────────────────────────
def dashboard_summary(plant_id) -> dict:
    from apps.controls.models import ControlInstance
    from apps.governance.services import get_vacant_mandatory_roles
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.plants.models import Plant
    from apps.plants.services import get_active_framework_codes
    from apps.risk.models import RiskAssessment
    from apps.tasks.models import Task

    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
    today = timezone.localdate()
    fw_codes = get_active_framework_codes(plant) if plant else []

    ci_qs = ControlInstance.objects.filter(deleted_at__isnull=True)
    if plant:
        ci_qs = ci_qs.filter(plant=plant, control__framework__code__in=fw_codes)
    total_ci = ci_qs.count()
    compliant = ci_qs.filter(status="compliant").count()
    gap = ci_qs.filter(status="gap").count()

    risk_qs = RiskAssessment.objects.filter(status="completato", deleted_at__isnull=True)
    if plant:
        risk_qs = risk_qs.filter(plant=plant)

    inc_qs = Incident.objects.filter(status__in=["aperto", "in_analisi"])
    if plant:
        inc_qs = inc_qs.filter(plant=plant)

    task_qs = Task.objects.filter(status__in=["aperto", "in_corso"], due_date__lt=today)
    if plant:
        task_qs = task_qs.filter(plant=plant)

    pdca_qs = PdcaCycle.objects.exclude(fase_corrente="chiuso")
    if plant:
        pdca_qs = pdca_qs.filter(plant=plant)

    incidents_open = inc_qs.count()
    pct_compliant = round(compliant / total_ci * 100, 1) if total_ci > 0 else 0

    return {
        "plants_active": Plant.objects.filter(deleted_at__isnull=True).count(),
        "controls_total": total_ci,
        "controls_compliant": compliant,
        "controls_gap": gap,
        "pct_compliant": pct_compliant,
        "incidents_open": incidents_open,
        "plant_id": plant_id,
        "frameworks": fw_codes,
        "tasks_overdue": task_qs.count(),
        "pdca_open": pdca_qs.count(),
        "risks_red": risk_qs.filter(score__gt=14).count(),
        "risks_yellow": risk_qs.filter(score__gt=7, score__lte=14).count(),
        "incidents_nis2": inc_qs.filter(nis2_notifiable="si").count(),
        "vacant_roles": get_vacant_mandatory_roles(plant) if plant else [],
    }


# ───────────────────────────────────────────────────────────────────────────
# KPI overview (governance GRC)
# ───────────────────────────────────────────────────────────────────────────
def kpi_overview(plant_id) -> dict:
    plant = None
    if plant_id:
        from apps.plants.models import Plant
        plant = Plant.objects.filter(pk=plant_id).first()

    return {
        "required_docs": _required_docs(plant),
        "mttr": _mttr(plant_id),
        "training": _training(plant),
        "supplier_nda": _supplier_nda(plant),
    }


def _required_docs(plant):
    from apps.compliance_schedule.services import get_required_documents_status
    from apps.plants.services import get_active_framework_codes

    ALL_FRAMEWORKS = ["ISO27001", "NIS2", "ACN_NIS2", "TISAX_L2", "TISAX_L3"]
    frameworks = get_active_framework_codes(plant) if plant else ALL_FRAMEWORKS

    result = []
    for fw in frameworks:
        items = get_required_documents_status(plant=plant, framework=fw)
        total = len(items)
        if total == 0:
            # Nessun RequiredDocument configurato: mostra la copertura dei controlli
            from apps.controls.models import ControlInstance
            ci_qs = ControlInstance.objects.filter(
                control__framework__code=fw, deleted_at__isnull=True,
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


def _mttr(plant_id):
    from apps.audit_prep.models import AuditFinding
    from apps.incidents.models import Incident
    from apps.tasks.models import Task

    duration_expr = ExpressionWrapper(
        F("closed_at") - F("created_at"), output_field=DurationField(),
    )
    task_duration_expr = ExpressionWrapper(
        F("completed_at") - F("created_at"), output_field=DurationField(),
    )

    def td_to_days(td):
        if td is None:
            return None
        return round(td.total_seconds() / 86400, 1)

    # Findings
    f_base = AuditFinding.objects.filter(closed_at__isnull=False, deleted_at__isnull=True)
    if plant_id:
        f_base = f_base.filter(audit_prep__plant_id=plant_id)

    # Chiavi di output stabili (attese dal frontend) → codici reali del modello.
    # I valori del campo sono `major_nc`/`minor_nc`/`observation`: filtrare per
    # "major"/"minor" (come faceva la view) dava sempre count 0 per quelle voci.
    finding_type_map = {"major": "major_nc", "minor": "minor_nc", "observation": "observation"}
    findings = {}
    for out_key, ftype in finding_type_map.items():
        agg = f_base.filter(finding_type=ftype).annotate(dur=duration_expr).aggregate(
            count=Count("id"), avg=Avg("dur")
        )
        findings[out_key] = {"count": agg["count"], "avg_days": td_to_days(agg["avg"])}
    findings["all"] = {
        "count": f_base.count(),
        "avg_days": td_to_days(
            f_base.annotate(dur=duration_expr).aggregate(avg=Avg("dur"))["avg"]
        ),
    }

    # Incidents
    i_base = Incident.objects.filter(closed_at__isnull=False, deleted_at__isnull=True)
    if plant_id:
        i_base = i_base.filter(plant_id=plant_id)

    incidents_all = i_base.annotate(dur=duration_expr).aggregate(count=Count("id"), avg=Avg("dur"))
    incidents_by_sev = {}
    for sev in ("critica", "alta", "media", "bassa"):
        agg = i_base.filter(severity=sev).annotate(dur=duration_expr).aggregate(
            count=Count("id"), avg=Avg("dur")
        )
        if agg["count"]:
            incidents_by_sev[sev] = {"count": agg["count"], "avg_days": td_to_days(agg["avg"])}

    # Tasks
    t_base = Task.objects.filter(
        status="completato", completed_at__isnull=False, deleted_at__isnull=True,
    )
    if plant_id:
        t_base = t_base.filter(plant_id=plant_id)

    tasks_all = t_base.annotate(dur=task_duration_expr).aggregate(count=Count("id"), avg=Avg("dur"))

    return {
        "findings": findings,
        "incidents": {
            "all": {"count": incidents_all["count"], "avg_days": td_to_days(incidents_all["avg"])},
            "by_severity": incidents_by_sev,
        },
        "tasks": {
            "all": {"count": tasks_all["count"], "avg_days": td_to_days(tasks_all["avg"])},
        },
    }


def _training(plant):
    from django.contrib.auth import get_user_model

    from apps.auth_grc.models import UserPlantAccess
    from apps.training.models import TrainingCourse, TrainingEnrollment

    User = get_user_model()

    # Perimetro: utenti attivi con almeno un accesso GRC non eliminato.
    if plant:
        accessible_ids = (
            UserPlantAccess.objects.filter(deleted_at__isnull=True)
            .filter(Q(scope_plants=plant) | Q(scope_plants__isnull=True))
            .values_list("user_id", flat=True)
        )
        user_qs = User.objects.filter(id__in=accessible_ids, is_active=True).distinct()
    else:
        user_qs = User.objects.filter(
            plant_access__deleted_at__isnull=True, is_active=True,
        ).distinct()

    total_users = user_qs.count()
    user_ids = list(user_qs.values_list("id", flat=True))

    course_qs = TrainingCourse.objects.filter(mandatory=True, status="attivo")
    if plant:
        course_qs = course_qs.filter(plants=plant)

    mandatory_courses = []
    mandatory_course_ids = list(course_qs.values_list("id", flat=True))

    for course in course_qs.order_by("title"):
        enrolled = TrainingEnrollment.objects.filter(course=course, user_id__in=user_ids).count()
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

    if mandatory_course_ids and user_ids:
        users_all_done = 0
        for uid in user_ids:
            completed_count = TrainingEnrollment.objects.filter(
                user_id=uid, course_id__in=mandatory_course_ids, status="completato",
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


def _supplier_nda(plant):
    from apps.suppliers.models import Supplier

    today = timezone.localdate()
    threshold_90 = today + timezone.timedelta(days=90)

    supplier_qs = Supplier.objects.filter(status="attivo", deleted_at__isnull=True)
    if plant:
        # include fornitori associati al plant + quelli globali (plants=[])
        supplier_qs = supplier_qs.filter(Q(plants=plant) | Q(plants__isnull=True)).distinct()

    total = supplier_qs.count()

    with_approved = supplier_qs.filter(
        nda_documents__document_type="contratto",
        nda_documents__status="approvato",
        nda_documents__deleted_at__isnull=True,
    ).distinct().count()

    expiring = supplier_qs.filter(
        nda_documents__document_type="contratto",
        nda_documents__status="approvato",
        nda_documents__deleted_at__isnull=True,
        nda_documents__expiry_date__lte=threshold_90,
        nda_documents__expiry_date__gte=today,
    ).distinct().count()

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
        days_to_expiry = (expiry_date - today).days if expiry_date else None

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


# ───────────────────────────────────────────────────────────────────────────
# KPI suggestion engine (catalogo standard → suggerimenti)
# ───────────────────────────────────────────────────────────────────────────
def kpi_suggest(plant_id, lang) -> dict:
    """Suggerisce KPI standard dal catalogo in base ai framework attivi del plant.
    Pura lettura: non crea nulla."""
    from apps.plants.models import Plant
    from apps.plants.services import get_active_framework_codes
    from apps.tasks.kpi_catalog import localized_catalog
    from apps.tasks.models import ChecklistTemplate, KPIDefinition

    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None

    plant_frameworks = get_active_framework_codes(plant) if plant else []
    fw_set = set(plant_frameworks)

    templates = list(
        ChecklistTemplate.objects.filter(deleted_at__isnull=True)
        .filter(Q(plant=plant) | Q(plant__isnull=True))
        .values("id", "name")
    )

    configured_codes = set(KPIDefinition.objects.values_list("kpi_code", flat=True))

    def _match_template(keywords):
        for kw in keywords or []:
            kw_l = kw.lower()
            for tpl in templates:
                if kw_l in (tpl["name"] or "").lower():
                    return {"id": str(tpl["id"]), "name": tpl["name"]}
        return None

    suggestions = []
    for item in localized_catalog(lang):
        if fw_set and not (set(item["frameworks"]) & fw_set):
            continue
        is_checklist = item["source"] == "checklist"
        matched_template = _match_template(item["match_keywords"]) if is_checklist else None
        suggestions.append({
            "kpi_code": item["kpi_code"],
            "name": item["name"],
            "description": item["description"],
            "unit": item["unit"],
            "aggregation": item["aggregation"],
            "threshold_direction": item["threshold_direction"],
            "threshold_warning": item["threshold_warning"],
            "threshold_critical": item["threshold_critical"],
            "notify_on_warning": item["notify_on_warning"],
            "notify_on_critical": item["notify_on_critical"],
            "source": item["source"],
            "category": item["category"],
            "frameworks": item["frameworks"],
            "rationale": item["rationale"],
            "checklist_hint": item["checklist_hint"],
            "already_configured": item["kpi_code"] in configured_codes,
            "suggested_checklist_template": matched_template,
            "can_create_template": (
                is_checklist and item["has_template_seed"] and matched_template is None
            ),
            "template_seed_name": item["template_seed_name"],
        })

    return {"plant_frameworks": plant_frameworks, "suggestions": suggestions}


# ───────────────────────────────────────────────────────────────────────────
# Matrice Accessi & Responsabilità (M18 / access review ISO 27001 A.9.2.5)
# ───────────────────────────────────────────────────────────────────────────
def access_matrix(plant_id=None, lang: str = "it") -> dict:
    """Matrice di chi-fa-cosa per validare gli accessi in qualunque momento.

    Aggrega per utente attivo due categorie:
      - ACCESSO tecnico (UserPlantAccess / GrcRole) → guida i permessi
      - RESPONSABILITÀ normativa (RoleAssignment governance / NormativeRole)

    Con `plant_id` mostra solo righe il cui scope copre quel sito; senza, è
    org-wide. Calcola flag di coerenza (responsabilità senza accesso, utente
    non attivo, in scadenza) e i ruoli obbligatori vacanti.
    """
    from django.utils import timezone
    from django.utils.translation import gettext, override

    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.governance.models import NormativeRole, RoleAssignment
    from apps.governance.services import get_vacant_mandatory_roles
    from apps.plants.models import Plant

    today = timezone.localdate()
    EXPIRY_DAYS = 30

    # ── Lookup siti/BU (una query ciascuno; tabelle piccole) ────────────────
    plants = {
        p.id: p for p in Plant.objects.filter(deleted_at__isnull=True).select_related("bu")
    }
    target = plants.get(_to_uuid(plant_id)) if plant_id else None
    all_plant_ids = set(plants.keys())
    bu_to_plant_ids: dict = {}
    for p in plants.values():
        if p.bu_id:
            bu_to_plant_ids.setdefault(p.bu_id, set()).add(p.id)

    def _codes(ids) -> list:
        return sorted(plants[i].code for i in ids if i in plants)

    # Risolve uno scope (di accesso o responsabilità) in (covers_all, plant_ids, label)
    def _resolve_access_scope(a) -> tuple:
        if a.scope_type == "org":
            return True, all_plant_ids, gettext("Tutti i siti")
        if a.scope_type == "bu" and a.scope_bu_id:
            ids = bu_to_plant_ids.get(a.scope_bu_id, set())
            label = f"{gettext('BU')}: {a.scope_bu.code}" if a.scope_bu else gettext("BU")
            return False, ids, label
        # plant_list / single_plant
        ids = {p.id for p in a.scope_plants.all()}
        return False, ids, ", ".join(_codes(ids)) or gettext("(nessun sito)")

    def _resolve_resp_scope(r) -> tuple:
        if r.scope_type == "org":
            return True, all_plant_ids, gettext("Tutti i siti")
        if r.scope_type == "bu" and r.scope_id:
            ids = bu_to_plant_ids.get(r.scope_id, set())
            return False, ids, gettext("BU")
        if r.scope_type == "plant" and r.scope_id:
            pid = r.scope_id
            return False, ({pid} if pid in plants else set()), ", ".join(_codes({pid}))
        return False, set(), gettext("(nessun sito)")

    def _covers_target(covers_all, ids) -> bool:
        # Senza filtro plant: includi tutto. Con filtro: org copre sempre.
        if target is None:
            return True
        return covers_all or target.id in ids

    # ── Accessi per utente (per il check responsabilità-senza-accesso) ──────
    access_qs = (
        UserPlantAccess.objects.filter(deleted_at__isnull=True)
        .select_related("user", "scope_bu")
        .prefetch_related("scope_plants")
    )
    access_by_user: dict = {}      # user_id -> {"all": bool, "ids": set}
    access_rows_raw: list = []
    for a in access_qs:
        covers_all, ids, label = _resolve_access_scope(a)
        cov = access_by_user.setdefault(a.user_id, {"all": False, "ids": set()})
        cov["all"] = cov["all"] or covers_all
        cov["ids"] |= ids
        access_rows_raw.append((a, covers_all, ids, label))

    # ── Responsabilità governance attive ────────────────────────────────────
    resp_qs = (
        RoleAssignment.objects.filter(deleted_at__isnull=True, valid_from__lte=today)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        .select_related("user")
    )

    rows: list = []
    user_ids_seen: set = set()

    with override(lang):
        grc_labels = {c.value: c.label for c in GrcRole}
        norm_labels = {c.value: c.label for c in NormativeRole}

        for a, covers_all, ids, label in access_rows_raw:
            if not _covers_target(covers_all, ids):
                continue
            u = a.user
            user_ids_seen.add(u.id)
            flags = []
            if not u.is_active:
                flags.append("inactive_user")
            rows.append({
                "user_id": str(u.id),
                "user_name": (f"{u.first_name} {u.last_name}".strip() or u.email or u.username),
                "user_email": u.email,
                "is_active": u.is_active,
                "kind": "access",
                "role": a.role,
                "role_label": str(grc_labels.get(a.role, a.role)),
                "scope_type": a.scope_type,
                "scope_label": label,
                "plant_codes": [] if covers_all else _codes(ids),
                "covers_all": covers_all,
                "valid_until": None,
                "flags": flags,
            })

        for r in resp_qs:
            covers_all, ids, label = _resolve_resp_scope(r)
            if not _covers_target(covers_all, ids):
                continue
            u = r.user
            user_ids_seen.add(u.id)
            flags = []
            if not u.is_active:
                flags.append("inactive_user")
            # Responsabilità senza un accesso che copra lo stesso perimetro
            cov = access_by_user.get(u.id)
            has_access = bool(cov and (cov["all"] or covers_all or (cov["ids"] & ids)))
            if not has_access:
                flags.append("responsibility_without_access")
            if r.valid_until and today <= r.valid_until <= today + timezone.timedelta(days=EXPIRY_DAYS):
                flags.append("expiring")
            rows.append({
                "user_id": str(u.id),
                "user_name": (f"{u.first_name} {u.last_name}".strip() or u.email or u.username),
                "user_email": u.email,
                "is_active": u.is_active,
                "kind": "responsibility",
                "role": r.role,
                "role_label": str(norm_labels.get(r.role, r.role)),
                "scope_type": r.scope_type,
                "scope_label": label,
                "plant_codes": [] if covers_all else _codes(ids),
                "covers_all": covers_all,
                "valid_until": str(r.valid_until) if r.valid_until else None,
                "flags": flags,
            })

    rows.sort(key=lambda x: (x["user_name"].lower(), x["kind"], x["role"]))
    vacant = get_vacant_mandatory_roles(target)
    issues = sum(1 for x in rows if x["flags"])

    return {
        "generated_at": timezone.now().isoformat(),
        "plant_id": str(target.id) if target else None,
        "plant_code": target.code if target else None,
        "rows": rows,
        "vacant_mandatory_roles": vacant,
        "summary": {
            "users": len(user_ids_seen),
            "access": sum(1 for x in rows if x["kind"] == "access"),
            "responsibilities": sum(1 for x in rows if x["kind"] == "responsibility"),
            "issues": issues,
        },
    }


def _to_uuid(value):
    """Converte una stringa in UUID per il lookup nel dict plants (None-safe)."""
    import uuid
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
