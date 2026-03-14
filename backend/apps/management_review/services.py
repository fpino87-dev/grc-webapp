from django.utils import timezone
from core.audit import log_action
from .models import ManagementReview


def get_kpi_snapshot(plant_id) -> dict:
    """Return a dict with key metrics for the given plant."""
    from django.db.models import Count, Q
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
    from django.db.models import Count, Q
    from apps.controls.models import Framework, ControlInstance
    from apps.documents.models import Document, Evidence
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.tasks.models import Task
    from apps.bcp.services import check_missing_bcp_plans

    plant_id = review.plant_id
    today = timezone.now().date()
    since_12m = timezone.now() - timezone.timedelta(days=365)

    # ── 1. Compliance per framework con dettaglio ──
    frameworks_detail = {}
    for fw in Framework.objects.filter(archived_at__isnull=True):
        qs = ControlInstance.objects.filter(
            plant_id=plant_id, control__framework=fw
        ).select_related("control__domain")
        total = qs.count()
        if total == 0:
            continue
        by_status = dict(qs.values("status").annotate(n=Count("id")).values_list("status", "n"))
        compliant = by_status.get("compliant", 0)

        gap_controls = list(qs.filter(status="gap").values(
            "id", "control__external_id", "control__translations",
        )[:20])

        expired_evidence_controls = list(qs.filter(
            status="compliant",
            evidences__valid_until__lt=today,
        ).values("id", "control__external_id")[:10])

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
    docs_summary = {
        "totale": docs_qs.count(),
        "approvati": docs_qs.filter(status="approvato").count(),
        "in_revisione": docs_qs.filter(status__in=["revisione", "approvazione"]).count(),
        "bozza": docs_qs.filter(status="bozza").count(),
        "in_scadenza": docs_qs.filter(
            status="approvato",
            review_due_date__lte=today + timezone.timedelta(days=90),
            review_due_date__gte=today,
        ).count(),
        "scaduti": docs_qs.filter(status="approvato", review_due_date__lt=today).count(),
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
    risk_summary = {
        "rosso":  risks_qs.filter(score__gt=14).count(),
        "giallo": risks_qs.filter(score__gt=7, score__lte=14).count(),
        "verde":  risks_qs.filter(score__lte=7).count(),
        "senza_piano": risks_qs.filter(score__gt=14, mitigation_plans__isnull=True).count(),
        "senza_owner": risks_qs.filter(owner__isnull=True).count(),
    }
    risks_by_owner = list(
        risks_qs.values("owner__first_name", "owner__last_name", "owner__email").annotate(
            totale=Count("id"),
            rossi=Count("id", filter=Q(score__gt=14)),
        ).order_by("-rossi")[:10]
    )

    # ── 4. Incidenti ──
    incidents_summary = {
        "totale_12m": Incident.objects.filter(plant_id=plant_id, created_at__gte=since_12m).count(),
        "nis2_notificati": Incident.objects.filter(
            plant_id=plant_id, nis2_notifiable="si", created_at__gte=since_12m
        ).count(),
        "aperti": Incident.objects.filter(plant_id=plant_id, status__in=["aperto", "in_analisi"]).count(),
        "senza_rca": Incident.objects.filter(
            plant_id=plant_id, status="chiuso", rca__isnull=True
        ).count(),
    }

    # ── 5. PDCA ──
    pdca_summary = {
        "aperti": PdcaCycle.objects.filter(plant_id=plant_id).exclude(fase_corrente="chiuso").count(),
        "bloccati_plan_90gg": PdcaCycle.objects.filter(
            plant_id=plant_id, fase_corrente="plan",
            created_at__lt=timezone.now() - timezone.timedelta(days=90),
        ).count(),
        "chiusi_12m": PdcaCycle.objects.filter(
            plant_id=plant_id, fase_corrente="chiuso", closed_at__gte=since_12m,
        ).count(),
    }

    # ── 6. BCP ──
    class _FakePlant:
        def __init__(self, pk):
            self.pk = pk
            self.id = pk

    missing_bcp = check_missing_bcp_plans(_FakePlant(plant_id)) if plant_id else []
    bcp_summary = {
        "processi_critici_senza_bcp": len(missing_bcp),
        "nomi": [p.name for p in missing_bcp[:5]],
    }

    # ── 7. Task scaduti ──
    tasks_summary = {
        "scaduti": Task.objects.filter(
            plant_id=plant_id,
            status__in=["aperto", "in_corso"],
            due_date__lt=today,
        ).count(),
        "critici_aperti": Task.objects.filter(
            plant_id=plant_id,
            priority="critica",
            status__in=["aperto", "in_corso"],
        ).count(),
    }

    snapshot = {
        "generated_at":   timezone.now().isoformat(),
        "plant_id":       str(plant_id) if plant_id else None,
        "frameworks":     frameworks_detail,
        "documenti":      {**docs_summary, "evidenze_scadute": ev_scadute, "evidenze_in_scadenza": ev_in_scadenza},
        "rischi":         risk_summary,
        "risks_by_owner": risks_by_owner,
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
            "Generare lo snapshot dei dati prima di approvare il riesame."
        )
    if review.approval_status == "approvato":
        raise ValidationError("Il riesame è già approvato.")

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
        payload={"review_id": str(review.pk), "note": note},
    )
    return review
