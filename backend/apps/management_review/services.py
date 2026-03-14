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
    Chiama i servizi degli altri moduli e salva in snapshot_data.
    """
    from apps.controls.services import get_compliance_summary
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle

    plant_id = review.plant_id

    # Compliance per framework
    frameworks_data = {}
    from apps.controls.models import Framework
    for fw in Framework.objects.filter(archived_at__isnull=True):
        frameworks_data[fw.code] = get_compliance_summary(plant_id, fw.code)

    # Rischi aperti per livello
    risks = RiskAssessment.objects.filter(
        plant_id=plant_id, status="completato", deleted_at__isnull=True
    )
    risk_summary = {
        "rosso":  risks.filter(score__gt=14).count(),
        "giallo": risks.filter(score__gt=7, score__lte=14).count(),
        "verde":  risks.filter(score__lte=7).count(),
    }

    # Rischi per owner
    from django.db.models import Count, Q
    risks_by_owner = list(
        risks.values(
            "owner__first_name", "owner__last_name", "owner__email"
        ).annotate(
            totale=Count("id"),
            rossi=Count("id", filter=Q(score__gt=14)),
        ).order_by("-rossi")[:10]
    )

    # Incidenti ultimi 12 mesi
    since = timezone.now() - timezone.timedelta(days=365)
    incidents_summary = {
        "totale":  Incident.objects.filter(plant_id=plant_id, created_at__gte=since).count(),
        "nis2":    Incident.objects.filter(plant_id=plant_id, nis2_notifiable="si", created_at__gte=since).count(),
        "aperti":  Incident.objects.filter(plant_id=plant_id, status="aperto").count(),
    }

    # PDCA aperti
    pdca_summary = {
        "aperti":  PdcaCycle.objects.filter(plant_id=plant_id).exclude(fase_corrente="chiuso").count(),
        "scaduti": PdcaCycle.objects.filter(
            plant_id=plant_id, fase_corrente="plan",
            created_at__lt=timezone.now() - timezone.timedelta(days=90),
        ).count(),
    }

    snapshot = {
        "generated_at":   timezone.now().isoformat(),
        "plant_id":       str(plant_id) if plant_id else None,
        "frameworks":     frameworks_data,
        "risk_summary":   risk_summary,
        "risks_by_owner": risks_by_owner,
        "incidents":      incidents_summary,
        "pdca":           pdca_summary,
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
