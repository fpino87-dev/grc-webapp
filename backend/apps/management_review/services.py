from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action
from .models import ManagementReview

# Gli elenchi di dettaglio nello snapshot sono pensati per la direzione:
# pochi elementi, i più rilevanti; il totale resta nei contatori.
SNAPSHOT_LIST_LIMIT = 10

# Soglia di rischio "critico" (rosso), coerente con il resto del modulo.
CRITICAL_RISK_SCORE = 14


def _display_name(first_name, last_name, email) -> str:
    name = f"{first_name or ''} {last_name or ''}".strip()
    return name or email or ""


def _iso(value):
    return value.isoformat() if value else None


def suggest_chair(plant_id=None):
    """Titolare suggerito per presiedere il riesame.

    CISO nominato sul sito, altrimenti CISO a livello organizzazione, altrimenti
    ISMS Manager (stesso ordine). Solo un suggerimento: l'utente può cambiarlo.
    """
    from apps.governance.services import _active_role_qs

    for role in ("ciso", "isms_manager"):
        qs = _active_role_qs(role).select_related("user").order_by("valid_from")
        if plant_id:
            hit = qs.filter(scope_type="plant", scope_id=plant_id).first()
            if hit:
                return hit.user
        hit = qs.filter(scope_type="org").first()
        if hit:
            return hit.user
    return None


def check_review_editable(review: ManagementReview, changed_fields) -> None:
    """Chair e partecipanti fanno parte del verbale: bloccati dopo l'approvazione."""
    from django.core.exceptions import ValidationError

    locked = {"chair", "attendees"} & set(changed_fields)
    if locked and review.approval_status == "approvato":
        raise ValidationError(
            _("Presidente e partecipanti non sono modificabili dopo l'approvazione del riesame.")
        )


def get_operational_kpi_summary(plant_id) -> dict:
    """Ultimo snapshot di ogni KPI operativo rilevante per il plant.

    P2-4 (catena KPI engine → revisione direzione): la revisione di direzione
    (ISO 27001 §9.3) deve considerare i "risultati di monitoraggio e misurazione".
    Il KPI engine (M08) produce snapshot settimanali con soglie e stato, ma la
    revisione finora li ignorava. Qui aggreghiamo, per ogni `KPIDefinition`
    attiva, lo snapshot più recente rilevante per il plant — sia i KPI specifici
    del plant sia i KPI globali (snapshot per-plant prodotti dal compute, oppure
    snapshot globali `plant=None` da ingest API).
    """
    from django.db.models import Q
    from apps.tasks.models import OperationalKpiSnapshot

    snaps = (
        OperationalKpiSnapshot.objects
        .filter(Q(plant_id=plant_id) | Q(plant__isnull=True))
        .filter(kpi_definition__is_active=True, kpi_definition__deleted_at__isnull=True)
        .select_related("kpi_definition")
        .order_by("kpi_definition_id", "-week_start", "-created_at")
    )

    latest: dict = {}
    for s in snaps:
        # Per ogni KPI tieni solo il primo (= più recente, per via dell'order_by);
        # a parità di plant_id/None preferisci lo snapshot legato al plant.
        prev = latest.get(s.kpi_definition_id)
        if prev is None:
            latest[s.kpi_definition_id] = s
        elif prev.plant_id is None and s.plant_id is not None and s.week_start == prev.week_start:
            latest[s.kpi_definition_id] = s

    status_counts = {"ok": 0, "warning": 0, "critical": 0, "no_data": 0}
    items = []
    for s in latest.values():
        kd = s.kpi_definition
        status_counts[s.status] = status_counts.get(s.status, 0) + 1
        items.append({
            "kpi_code": kd.kpi_code,
            "name": kd.name,
            "unit": kd.unit,
            "value": s.value,
            "status": s.status,
            "threshold_warning": kd.threshold_warning,
            "threshold_critical": kd.threshold_critical,
            "threshold_direction": kd.threshold_direction,
            "week_start": s.week_start.isoformat(),
            "scope": "plant" if s.plant_id else "global",
        })

    items.sort(key=lambda x: x["kpi_code"])
    return {
        "items": items,
        "count": len(items),
        "status_counts": status_counts,
        "attention": status_counts["warning"] + status_counts["critical"],
    }


def get_kpi_snapshot(plant_id) -> dict:
    """Return a dict with key metrics for the given plant."""
    from apps.controls.models import ControlInstance
    from apps.incidents.models import Incident
    from apps.risk.models import RiskAssessment

    controls_qs = ControlInstance.objects.filter(plant_id=plant_id)
    total_controls = controls_qs.count()
    compliant = controls_qs.filter(status="compliant").count()

    incidents_qs = Incident.objects.filter(plant_id=plant_id)
    open_incidents = incidents_qs.filter(status__in=["aperto", "in_analisi"]).count()

    risks_qs = RiskAssessment.objects.filter(plant_id=plant_id, status="completato")
    high_risks = risks_qs.filter(score__gt=14).count()

    return {
        "plant_id": str(plant_id),
        "controls_total": total_controls,
        "controls_compliant": compliant,
        "pct_compliant": round(compliant / total_controls * 100, 1) if total_controls else 0,
        "incidents_open": open_incidents,
        "risks_high": high_risks,
        "operational_kpis": get_operational_kpi_summary(plant_id),
        "snapshot_at": timezone.now().isoformat(),
    }


def complete_review(review: ManagementReview, user) -> ManagementReview:
    """Transition a review to completato and snapshot KPIs."""
    if review.plant_id:
        review.kpi_snapshot = get_kpi_snapshot(review.plant_id)
    review.status = "completato"
    review.save(update_fields=["status", "kpi_snapshot", "updated_at"])
    log_action(
        user=user,
        action_code="management_review.review.complete",
        level="L2",
        entity=review,
        payload={"id": str(review.id), "title": review.title},
    )
    return review


def generate_snapshot(review: ManagementReview, user) -> dict:
    """
    Congela i dati di compliance al momento della riunione.
    """
    from django.core.exceptions import ValidationError

    if review.approval_status == "approvato":
        # Lo snapshot è il contenuto del verbale approvato: non si riscrive.
        raise ValidationError(_("Il riesame è approvato: lo snapshot non può essere rigenerato."))

    from django.db.models import Case, Count, IntegerField, Q, Value, When
    from apps.controls.models import ControlInstance
    from apps.documents.models import Document, Evidence
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.tasks.models import Task

    plant_id = review.plant_id
    today = timezone.localdate()
    since_12m = timezone.now() - timezone.timedelta(days=365)

    # ── 1. Compliance per framework con dettaglio ──
    from apps.plants.services import get_active_frameworks
    from apps.plants.models import Plant as PlantModel
    _plant = PlantModel.objects.filter(pk=plant_id).first() if plant_id else None

    frameworks_detail = {}
    for fw in get_active_frameworks(_plant):
        qs = ControlInstance.objects.filter(
            plant_id=plant_id, control__framework=fw
        ).select_related("control__domain")
        total = qs.count()
        if total == 0:
            continue
        by_status = dict(qs.values("status").annotate(n=Count("id")).values_list("status", "n"))
        compliant = by_status.get("compliant", 0)

        gap_controls = [
            {
                "id": str(item["id"]),
                "control__external_id": item["control__external_id"],
                # Solo il titolo per lingua: il JSON completo delle traduzioni
                # (guida, evidenze attese…) non serve al verbale.
                "titles": {
                    lang: (tr or {}).get("title", "")
                    for lang, tr in (item["control__translations"] or {}).items()
                    if (tr or {}).get("title")
                },
            }
            for item in qs.filter(status="gap").order_by("control__external_id").values(
                "id", "control__external_id", "control__translations",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

        expired_evidence_controls = [
            {**item, "id": str(item["id"])}
            for item in qs.filter(
                status="compliant",
                evidences__valid_until__lt=today,
            ).values("id", "control__external_id")[:10]
        ]

        frameworks_detail[fw.code] = {
            "framework_name": fw.name,
            "total": total,
            "by_status": by_status,
            "pct_compliant": round(compliant / total * 100, 1) if total else 0,
            "gap_controls": gap_controls,
            "expired_evidence_count": len(expired_evidence_controls),
        }

    # ── 2. Documenti ──
    docs_qs = Document.objects.filter(plant_id=plant_id, deleted_at__isnull=True)
    expiring_q = Q(
        status="approvato",
        review_due_date__lte=today + timezone.timedelta(days=90),
        review_due_date__gte=today,
    )
    expired_q = Q(status="approvato", review_due_date__lt=today)

    # "Novità" da portare in direzione: approvati dall'ultimo riesame del
    # perimetro (o negli ultimi 12 mesi se è il primo).
    previous = (
        ManagementReview.objects.filter(plant_id=plant_id, review_date__lt=review.review_date)
        .exclude(pk=review.pk)
        .order_by("-review_date")
        .first()
    )
    approved_since = previous.review_date if previous else (today - timezone.timedelta(days=365))
    approved_recent_q = Q(status="approvato", approved_at__date__gte=approved_since)

    def _doc_items(q, order):
        return [
            {
                "id": str(d["id"]),
                "title": d["title"],
                "owner": _display_name(d["owner__first_name"], d["owner__last_name"], d["owner__email"]),
                "review_due_date": _iso(d["review_due_date"]),
                "approved_at": _iso(d["approved_at"]),
            }
            for d in docs_qs.filter(q).order_by(order).values(
                "id", "title", "review_due_date", "approved_at",
                "owner__first_name", "owner__last_name", "owner__email",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

    docs_summary = {
        "totale": docs_qs.count(),
        "approvati": docs_qs.filter(status="approvato").count(),
        "in_revisione": docs_qs.filter(status__in=["revisione", "approvazione"]).count(),
        "bozza": docs_qs.filter(status="bozza").count(),
        "in_scadenza": docs_qs.filter(expiring_q).count(),
        "scaduti": docs_qs.filter(expired_q).count(),
        "approvati_periodo": docs_qs.filter(approved_recent_q).count(),
        "approvati_dal": approved_since.isoformat(),
        "elenco_scaduti": _doc_items(expired_q, "review_due_date"),
        "elenco_in_scadenza": _doc_items(expiring_q, "review_due_date"),
        "elenco_approvati_periodo": _doc_items(approved_recent_q, "-approved_at"),
    }
    ev_scadute = Evidence.objects.filter(
        plant_id=plant_id, valid_until__lt=today, deleted_at__isnull=True
    ).count()
    ev_in_scadenza = Evidence.objects.filter(
        plant_id=plant_id,
        valid_until__gte=today,
        valid_until__lte=today + timezone.timedelta(days=30),
        deleted_at__isnull=True,
    ).count()

    # ── 3. Rischi ──
    risks_qs = RiskAssessment.objects.filter(
        plant_id=plant_id, status="completato", deleted_at__isnull=True
    )
    critical_qs = risks_qs.filter(score__gt=CRITICAL_RISK_SCORE)
    accepted_qs = risks_qs.filter(risk_accepted_formally=True)
    risk_summary = {
        "rosso":  critical_qs.count(),
        "giallo": risks_qs.filter(score__gt=7, score__lte=CRITICAL_RISK_SCORE).count(),
        "verde":  risks_qs.filter(score__lte=7).count(),
        "senza_piano": critical_qs.annotate(
            n_plans=Count("mitigation_plans", filter=Q(mitigation_plans__deleted_at__isnull=True))
        ).filter(n_plans=0).count(),
        "senza_owner": risks_qs.filter(owner__isnull=True).count(),
        "accettati_formalmente": accepted_qs.count(),
    }

    def _risk_items(qs, order):
        rows = (
            qs.select_related("asset", "critical_process", "owner", "risk_accepted_by")
            .annotate(n_plans=Count("mitigation_plans", filter=Q(mitigation_plans__deleted_at__isnull=True)))
            .order_by(*order)[:SNAPSHOT_LIST_LIMIT]
        )
        return [
            {
                "id": str(r.pk),
                "name": r.name or (r.asset.name if r.asset else "") or "—",
                "asset": r.asset.name if r.asset else None,
                "process": r.critical_process.name if r.critical_process else None,
                "inherent_score": r.inherent_score,
                "score": r.score,
                "treatment": r.treatment or None,
                "owner": _display_name(r.owner.first_name, r.owner.last_name, r.owner.email) if r.owner else None,
                "has_plan": r.n_plans > 0,
                "accepted_formally": r.risk_accepted_formally,
                "accepted_by": (
                    _display_name(r.risk_accepted_by.first_name, r.risk_accepted_by.last_name, r.risk_accepted_by.email)
                    if r.risk_accepted_by else None
                ),
                "acceptance_expiry": _iso(r.risk_acceptance_expiry),
            }
            for r in rows
        ]

    risk_summary["top_critici"] = _risk_items(critical_qs, ["-score", "-inherent_score"])
    risk_summary["elenco_accettati"] = _risk_items(accepted_qs, ["risk_acceptance_expiry", "-score"])

    # ── 4. Incidenti ──
    incidents_qs = Incident.objects.filter(plant_id=plant_id)
    open_inc_q = Q(status__in=["aperto", "in_analisi"])
    nis2_inc_q = Q(nis2_notifiable="si", created_at__gte=since_12m)

    def _incident_items(q):
        return [
            {
                "id": str(i["id"]),
                "title": i["title"],
                "detected_at": _iso(i["detected_at"]),
                "severity": i["severity"],
                "status": i["status"],
            }
            for i in incidents_qs.filter(q).order_by("-detected_at").values(
                "id", "title", "detected_at", "severity", "status",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

    incidents_summary = {
        "totale_12m": incidents_qs.filter(created_at__gte=since_12m).count(),
        "nis2_notificati": incidents_qs.filter(nis2_inc_q).count(),
        "aperti": incidents_qs.filter(open_inc_q).count(),
        "senza_rca": incidents_qs.filter(status="chiuso", rca__isnull=True).count(),
        "elenco_aperti": _incident_items(open_inc_q),
        "elenco_nis2": _incident_items(nis2_inc_q),
    }

    # ── 5. PDCA ──
    blocked_q = Q(fase_corrente="plan", created_at__lt=timezone.now() - timezone.timedelta(days=90))
    pdca_qs = PdcaCycle.objects.filter(plant_id=plant_id)
    pdca_summary = {
        "aperti": pdca_qs.exclude(fase_corrente__in=["chiuso", "archiviato"]).count(),
        "bloccati_plan_90gg": pdca_qs.filter(blocked_q).count(),
        "chiusi_12m": pdca_qs.filter(fase_corrente="chiuso", closed_at__gte=since_12m).count(),
        "elenco_bloccati": [
            {"id": str(c["id"]), "title": c["title"], "created_at": _iso(c["created_at"])}
            for c in pdca_qs.filter(blocked_q).order_by("created_at").values(
                "id", "title", "created_at",
            )[:SNAPSHOT_LIST_LIMIT]
        ],
    }

    # ── 6. BCP ──
    from apps.bia.models import CriticalProcess
    from apps.bcp.models import BcpPlan

    if plant_id:
        critical_procs = CriticalProcess.objects.filter(
            plant_id=plant_id,
            criticality__gte=4,
            status="approvato",
            deleted_at__isnull=True,
        ).prefetch_related(
            Prefetch(
                "bcp_plans",
                queryset=BcpPlan.objects.filter(deleted_at__isnull=True),
            )
        )
        missing_bcp = [p for p in critical_procs if not p.bcp_plans.all()]
    else:
        missing_bcp = []
    bcp_summary = {
        "processi_critici_senza_bcp": len(missing_bcp),
        "nomi": [p.name for p in missing_bcp[:5]],
    }

    # ── 7. Task scaduti ──
    open_tasks_qs = Task.objects.filter(plant_id=plant_id, status__in=["aperto", "in_corso"])
    overdue_qs = open_tasks_qs.filter(due_date__lt=today)
    priority_rank = Case(
        When(priority="critica", then=Value(0)),
        When(priority="alta", then=Value(1)),
        When(priority="media", then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    tasks_summary = {
        "scaduti": overdue_qs.count(),
        "critici_aperti": open_tasks_qs.filter(priority="critica").count(),
        # Prima i più gravi, poi i più in ritardo.
        "elenco_scaduti": [
            {
                "id": str(t["id"]),
                "title": t["title"],
                "priority": t["priority"],
                "due_date": _iso(t["due_date"]),
                "assigned_role": t["assigned_role"],
            }
            for t in overdue_qs.annotate(rank=priority_rank).order_by("rank", "due_date").values(
                "id", "title", "priority", "due_date", "assigned_role",
            )[:SNAPSHOT_LIST_LIMIT]
        ],
    }

    snapshot = {
        "generated_at":   timezone.now().isoformat(),
        "plant_id":       str(plant_id) if plant_id else None,
        "frameworks":     frameworks_detail,
        "documenti":      {**docs_summary, "evidenze_scadute": ev_scadute, "evidenze_in_scadenza": ev_in_scadenza},
        "rischi":         risk_summary,
        "incidenti":      incidents_summary,
        "pdca":           pdca_summary,
        "bcp":            bcp_summary,
        "task":           tasks_summary,
    }

    review.snapshot_data = snapshot
    review.snapshot_generated_at = timezone.now()
    review.save(update_fields=["snapshot_data", "snapshot_generated_at", "updated_at"])

    log_action(
        user=user,
        action_code="management_review.snapshot_generated",
        level="L2",
        entity=review,
        payload={"review_id": str(review.pk)},
    )
    return snapshot


def approve_review(review: ManagementReview, user, note="") -> ManagementReview:
    """Approva formalmente il riesame di direzione."""
    from django.core.exceptions import ValidationError

    if not review.snapshot_generated_at:
        raise ValidationError(
            _("Generare lo snapshot dei dati prima di approvare il riesame.")
        )
    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è già approvato."))

    review.approval_status = "approvato"
    review.approved_by = user
    review.approved_at = timezone.now()
    review.approval_note = note
    review.save(update_fields=[
        "approval_status", "approved_by", "approved_at",
        "approval_note", "updated_at",
    ])

    log_action(
        user=user,
        action_code="management_review.approved",
        level="L1",
        entity=review,
        payload={"review_id": str(review.pk), "note": (note or "")[:200]},
    )
    return review
