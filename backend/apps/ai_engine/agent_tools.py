"""
Tool deterministici per il GRC Compliance Assistant.

Ogni funzione:
- riceve `user` per RBAC + `plant_id` per scoping
- rispetta deleted_at__isnull=True
- ritorna dict JSON-serializable
- NON chiama mai l'LLM
- NON modifica mai dati
"""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from core.scoping import get_user_plant_ids, scope_queryset_by_plant


def _verify_plant_access(user, plant_id) -> bool:
    """True se l'utente puo' vedere oggetti di questo plant."""
    allowed = get_user_plant_ids(user)
    if allowed is None:  # superuser / scope org
        return True
    return str(plant_id) in {str(p) for p in allowed}


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


def get_expired_documents(user, plant_id, today=None) -> list[dict]:
    """
    Documenti del plant con expiry_date <= oggi OPPURE review_due_date <= oggi.
    Distingue "expired" da "review_due" nella response.
    """
    from apps.documents.models import Document

    today = today or timezone.now().date()
    if not _verify_plant_access(user, plant_id):
        return []

    qs = Document.objects.filter(deleted_at__isnull=True).filter(
        Q(plant_id=plant_id) | Q(shared_plants__id=plant_id)
    ).filter(
        Q(expiry_date__lte=today) | Q(review_due_date__lte=today)
    ).distinct().select_related("plant", "owner")
    qs = scope_queryset_by_plant(qs, user, plant_field="plant", allow_null_plant=True)

    out = []
    for doc in qs[:50]:
        is_expired = bool(doc.expiry_date and doc.expiry_date <= today)
        kind = "expired" if is_expired else "review_due"
        ref_date = doc.expiry_date if is_expired else doc.review_due_date
        days_overdue = (today - ref_date).days if ref_date else None
        out.append({
            "kind": kind,
            "id": str(doc.id),
            "title": doc.title,
            "document_type": doc.document_type,
            "status": doc.status,
            "expiry_date": str(doc.expiry_date) if doc.expiry_date else None,
            "review_due_date": str(doc.review_due_date) if doc.review_due_date else None,
            "days_overdue": days_overdue,
            "owner_email_masked": _mask_email(doc.owner.email) if doc.owner else None,
            "frontend_url": f"/documents?id={doc.id}",
        })
    return out


def get_missing_evidences(user, plant_id) -> list[dict]:
    """
    Restituisce le ControlInstance non-compliant e non-N/A del plant
    (status in: gap, parziale, non_valutato). Per ogni istanza calcola
    eventuali dettagli su evidenze/documenti mancanti via
    check_evidence_requirements (informativi: il filtro principale e' lo
    status field, che riflette la valutazione esplicita dell'utente).

    Esclusioni:
    - status="compliant" (l'utente ha dichiarato OK)
    - status="na" (fuori contesto organizzativo: serve solo il motivo
      di esclusione, non evidenze)

    Dedup gerarchico: se il controllo e' coperto da un extender (es. TISAX L2
    quando l'evidenza e' caricata su TISAX L3 che lo estende), non viene
    emesso il gap. Stessa semantica usata da audit_prep.validation tramite
    apps.controls.services.is_covered_by_extender.
    """
    from apps.controls.models import ControlInstance
    from apps.controls.services import check_evidence_requirements, is_covered_by_extender

    if not _verify_plant_access(user, plant_id):
        return []

    today = timezone.now().date()
    qs = ControlInstance.objects.filter(
        plant_id=plant_id,
        deleted_at__isnull=True,
        status__in=["gap", "parziale", "non_valutato"],
    ).select_related("control", "control__framework")
    qs = scope_queryset_by_plant(qs, user, plant_field="plant")

    out = []
    for ci in qs:
        if is_covered_by_extender(ci, today):
            continue
        check = check_evidence_requirements(ci)
        out.append({
            "control_instance_id": str(ci.id),
            "control_external_id": ci.control.external_id,
            "control_title": ci.control.get_title("it"),
            "framework_code": ci.control.framework.code if ci.control.framework else "",
            "status": ci.status,
            "missing_documents": check["missing_documents"],
            "missing_evidences": check["missing_evidences"],
            "expired_evidences": check["expired_evidences"],
            "warnings": check["warnings"],
            "frontend_url": f"/controls?id={ci.id}",
        })
    return out


def get_expired_risk_assessments(user, plant_id, today=None) -> list[dict]:
    """
    RiskAssessment scaduti:
    - status=completato e (assessed_at + frequency policy) < oggi
    - OPPURE needs_revaluation=True
    """
    from apps.compliance_schedule.services import _add_duration, _get_rule
    from apps.plants.models import Plant
    from apps.risk.models import RiskAssessment

    today = today or timezone.now().date()
    if not _verify_plant_access(user, plant_id):
        return []

    plant = Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()
    freq_val, freq_unit, _alert = _get_rule("risk_assessment", plant)

    qs = RiskAssessment.objects.filter(
        plant_id=plant_id,
        deleted_at__isnull=True,
    ).filter(
        Q(needs_revaluation=True)
        | Q(status="completato", assessed_at__isnull=False)
    ).select_related("plant")
    qs = scope_queryset_by_plant(qs, user, plant_field="plant")

    out = []
    for ra in qs:
        is_expired = False
        next_due = None
        reason = None
        if ra.needs_revaluation:
            is_expired = True
            reason = "needs_revaluation"
        elif ra.assessed_at:
            next_due = _add_duration(ra.assessed_at.date(), freq_val, freq_unit)
            if next_due < today:
                is_expired = True
                reason = "assessment_expired"
        if not is_expired:
            continue
        out.append({
            "id": str(ra.id),
            "name": ra.name or f"Risk {ra.pk}",
            "assessment_type": ra.assessment_type,
            "status": ra.status,
            "score": ra.score,
            "reason": reason,
            "assessed_at": str(ra.assessed_at.date()) if ra.assessed_at else None,
            "next_due": str(next_due) if next_due else None,
            "days_overdue": (today - next_due).days if next_due else None,
            "frontend_url": f"/risk?id={ra.id}",
        })
    return out


def get_suppliers_without_assessment(user, plant_id, today=None) -> list[dict]:
    """
    Supplier collegati al plant che:
    - sono NIS2-relevant OPPURE risk_level alto/critico
    - non hanno SupplierAssessment in stato completato/approvato
    - OPPURE next_assessment_date < oggi
    """
    from apps.suppliers.models import Supplier

    today = today or timezone.now().date()
    if not _verify_plant_access(user, plant_id):
        return []

    sup_qs = Supplier.objects.filter(
        plants__id=plant_id,
        deleted_at__isnull=True,
    ).filter(
        Q(nis2_relevant=True) | Q(risk_level__in=["alto", "critico"])
    ).distinct()
    sup_qs = scope_queryset_by_plant(sup_qs, user, plant_field="plants")

    out = []
    for sup in sup_qs:
        last_completed = sup.assessments.filter(
            status__in=["completato", "approvato"],
            deleted_at__isnull=True,
        ).order_by("-assessment_date").first()
        next_due = last_completed.next_assessment_date if last_completed else None

        if last_completed and (not next_due or next_due >= today):
            continue  # ha un assessment valido

        reason = "never_assessed" if not last_completed else "assessment_expired"
        out.append({
            "id": str(sup.id),
            "name": sup.name,
            "risk_level": sup.risk_level,
            "nis2_relevant": sup.nis2_relevant,
            "status": sup.status,
            "reason": reason,
            "last_assessment_date": str(last_completed.assessment_date) if last_completed else None,
            "next_due": str(next_due) if next_due else None,
            "days_overdue": (today - next_due).days if next_due else None,
            "frontend_url": f"/suppliers?id={sup.id}",
        })
    return out
