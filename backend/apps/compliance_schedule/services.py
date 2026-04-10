"""
Central service for compliance deadlines and activity schedule.

get_due_date(rule_type, plant, from_date) — single entry point for all modules.
get_activity_schedule(plant, months_ahead) — aggregates expiring activities.
get_required_documents_status(plant, framework) — traffic-light for required docs.
"""
from __future__ import annotations

import datetime
import logging
from typing import Optional

from django.utils import timezone

from .models import (
    ComplianceSchedulePolicy,
    DEFAULT_RULES,
    RULE_TYPE_LABELS,
)

logger = logging.getLogger(__name__)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_active_policy(plant) -> Optional[ComplianceSchedulePolicy]:
    """Return the active policy for a plant, falling back to global."""
    if plant:
        p = ComplianceSchedulePolicy.objects.filter(plant=plant, is_active=True).first()
        if p:
            return p
    return ComplianceSchedulePolicy.objects.filter(plant__isnull=True, is_active=True).first()


def _get_rule(rule_type: str, plant) -> tuple[int, str, int]:
    """Return (frequency_value, frequency_unit, alert_days_before) from active policy or defaults."""
    policy = _get_active_policy(plant)
    if policy:
        rule = policy.rules.filter(rule_type=rule_type, enabled=True).first()
        if rule:
            return rule.frequency_value, rule.frequency_unit, rule.alert_days_before
    defaults = DEFAULT_RULES.get(rule_type)
    if defaults:
        return defaults
    return 365, "days", 30  # fallback: 1 year


def _add_duration(base: datetime.date, value: int, unit: str) -> datetime.date:
    if unit == "days":
        return base + datetime.timedelta(days=value)
    elif unit == "weeks":
        return base + datetime.timedelta(weeks=value)
    elif unit == "months":
        month = base.month - 1 + value
        year = base.year + month // 12
        month = month % 12 + 1
        day = min(base.day, [31,28,29,31,30,31,30,31,31,30,31,30,31][month])
        return datetime.date(year, month, day)
    elif unit == "years":
        try:
            return base.replace(year=base.year + value)
        except ValueError:
            return base.replace(year=base.year + value, day=28)
    return base + datetime.timedelta(days=value * 30)


# ─── Public API ───────────────────────────────────────────────────────────────

def get_due_date(rule_type: str, plant=None, from_date: Optional[datetime.date] = None) -> datetime.date:
    """Compute the next due date for rule_type starting from from_date (default: today)."""
    freq_val, freq_unit, _ = _get_rule(rule_type, plant)
    base = from_date or timezone.now().date()
    return _add_duration(base, freq_val, freq_unit)


def get_alert_threshold(rule_type: str, plant=None) -> int:
    """Return how many days before due date an alert should fire."""
    _, _, alert_days = _get_rule(rule_type, plant)
    return alert_days


def create_default_policy(plant=None, name: str = "Policy predefinita") -> ComplianceSchedulePolicy:
    """Create a ComplianceSchedulePolicy with all DEFAULT_RULES as ScheduleRule rows."""
    from .models import ScheduleRule
    from django.utils import timezone as tz

    policy = ComplianceSchedulePolicy.objects.create(
        plant=plant,
        name=name,
        is_active=True,
        valid_from=tz.now().date(),
    )
    rules = [
        ScheduleRule(
            policy=policy,
            rule_type=rule_type,
            frequency_value=freq_val,
            frequency_unit=freq_unit,
            alert_days_before=alert_days,
        )
        for rule_type, (freq_val, freq_unit, alert_days) in DEFAULT_RULES.items()
    ]
    ScheduleRule.objects.bulk_create(rules)
    return policy


# ─── Activity Schedule ────────────────────────────────────────────────────────

def get_activity_schedule(plant=None, months_ahead: int = 6) -> list[dict]:
    """
    Aggregate all upcoming expiring activities across GRC modules.
    Returns a list of dicts sorted by due_date ascending.
    """
    today = timezone.now().date()
    cutoff = _add_duration(today, months_ahead, "months")
    activities = []

    # Helper
    def _add(category: str, label: str, due: datetime.date | None, status: str = "ok", ref_id: str = "", url: str = ""):
        if due and today <= due <= cutoff:
            days_left = (due - today).days
            alert_days = get_alert_threshold(category, plant)
            urgency = "red" if days_left <= 7 else ("yellow" if days_left <= alert_days else "green")
            activities.append({
                "category": category,
                "category_label": RULE_TYPE_LABELS.get(category, category),
                "label": label,
                "due_date": str(due),
                "days_left": days_left,
                "urgency": urgency,
                "status": status,
                "ref_id": ref_id,
                "url": url,
            })

    plant_filter = {"plant": plant} if plant else {}

    # Documents expiring
    try:
        from apps.documents.models import Document

        doc_qs = Document.objects.filter(
            deleted_at__isnull=True,
            review_due_date__isnull=False,
        )
        if plant:
            doc_qs = doc_qs.filter(plant=plant)
        for doc in doc_qs:
            rule = (
                f"document_{doc.document_type}"
                if f"document_{doc.document_type}" in DEFAULT_RULES
                else "document_policy"
            )
            _add(rule, f"Doc: {doc.title}", doc.review_due_date, doc.status, str(doc.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze documenti", exc_info=True)

    # Evidences expiring
    try:
        from apps.documents.models import Evidence

        ev_qs = Evidence.objects.filter(valid_until__isnull=False)
        if plant:
            ev_qs = ev_qs.filter(control_instances__plant=plant).distinct()
        for ev in ev_qs:
            _add("control_review", f"Evidenza: {ev.title}", ev.valid_until, "active", str(ev.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze evidenze", exc_info=True)

    # Risk assessments — next review due
    try:
        from apps.risk.models import RiskAssessment

        risk_qs = RiskAssessment.objects.filter(status="completato", assessed_at__isnull=False)
        if plant:
            risk_qs = risk_qs.filter(**plant_filter)
        freq_val, freq_unit, _ = _get_rule("risk_assessment", plant)
        for ra in risk_qs:
            next_due = _add_duration(ra.assessed_at.date(), freq_val, freq_unit)
            _add("risk_assessment", f"Rischio: {ra.name}", next_due, ra.status, str(ra.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze risk assessment", exc_info=True)

    # BCP plans — next test date
    try:
        from apps.bcp.models import BcpPlan

        bcp_qs = BcpPlan.objects.filter(next_test_date__isnull=False)
        if plant:
            bcp_qs = bcp_qs.filter(**plant_filter)
        for plan in bcp_qs:
            _add("bcp_test", f"BCP Test: {plan.title}", plan.next_test_date, plan.status, str(plan.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze BCP", exc_info=True)

    # Supplier assessments
    try:
        from apps.suppliers.models import SupplierAssessment

        sa_qs = SupplierAssessment.objects.filter(next_assessment_date__isnull=False)
        if plant:
            sa_qs = sa_qs.filter(supplier__plant=plant)
        for sa in sa_qs:
            _add(
                "supplier_assessment",
                f"Fornitore: {sa.supplier.name}",
                sa.next_assessment_date,
                sa.status,
                str(sa.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze assessment fornitori", exc_info=True)

    # Supplier contracts expiring
    try:
        from apps.suppliers.models import Supplier

        sup_qs = Supplier.objects.filter(evaluation_date__isnull=False, deleted_at__isnull=True)
        if plant:
            sup_qs = sup_qs.filter(**plant_filter)
        for sup in sup_qs:
            _add(
                "supplier_contract_review",
                f"Contratto: {sup.name}",
                sup.evaluation_date,
                sup.status,
                str(sup.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze contratti fornitori", exc_info=True)

    # Training courses deadline
    try:
        from apps.training.models import TrainingCourse

        tr_qs = TrainingCourse.objects.filter(deadline__isnull=False, mandatory=True)
        if plant:
            tr_qs = tr_qs.filter(plants=plant)
        for tr in tr_qs:
            _add(
                "training_mandatory",
                f"Formazione: {tr.title}",
                tr.deadline,
                tr.status,
                str(tr.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze formazione", exc_info=True)

    # Security committee next meeting
    try:
        from apps.governance.models import SecurityCommittee

        sc_qs = SecurityCommittee.objects.filter(next_meeting_at__isnull=False)
        if plant:
            sc_qs = sc_qs.filter(plant=plant)
        for sc in sc_qs:
            _add(
                "security_committee",
                f"Comitato: {sc.name}",
                sc.next_meeting_at.date(),
                "scheduled",
                str(sc.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze comitato sicurezza", exc_info=True)

    # Audit findings
    try:
        from apps.audit_prep.models import AuditFinding

        af_qs = AuditFinding.objects.filter(
            response_deadline__isnull=False,
            status__in=["open", "in_response"],
        )
        if plant:
            af_qs = af_qs.filter(audit_prep__plant=plant)
        rule_map = {
            "major_nc": "finding_major",
            "minor_nc": "finding_minor",
            "observation": "finding_observation",
            "opportunity": "finding_observation",
        }
        for af in af_qs:
            rule_type = rule_map.get(af.finding_type, "finding_minor")
            _add(
                rule_type,
                f"Finding [{af.finding_type.upper()}]: {af.title}",
                af.response_deadline,
                af.status,
                str(af.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze finding audit", exc_info=True)

    activities.sort(key=lambda x: x["due_date"])
    return activities


# ─── Required documents status ────────────────────────────────────────────────

def get_required_documents_status(plant=None, framework: str = "ISO27001") -> list[dict]:
    """
    For each RequiredDocument of the given framework, check whether a matching
    Document exists in the plant. Returns traffic-light status.
    """
    # Verifica che il framework sia attivo per questo plant
    if plant:
        from apps.plants.services import get_active_framework_codes
        active_codes = get_active_framework_codes(plant)
        if framework not in active_codes:
            return []

    from .models import RequiredDocument
    required = RequiredDocument.objects.filter(framework=framework)
    result = []

    for req in required:
        try:
            from apps.documents.models import Document
            doc_qs = Document.objects.filter(
                document_type=req.document_type,
                deleted_at__isnull=True,
            )
            if plant:
                doc_qs = doc_qs.filter(plant=plant)
            doc = doc_qs.order_by("-updated_at").first()
        except Exception:
            doc = None

        if doc is None:
            traffic = "red"
            doc_info = None
        elif doc.status == "approvato":
            traffic = "green"
            doc_info = {"id": str(doc.id), "title": doc.title, "status": doc.status, "review_due_date": str(doc.review_due_date) if doc.review_due_date else None}
        else:
            traffic = "yellow"
            doc_info = {"id": str(doc.id), "title": doc.title, "status": doc.status, "review_due_date": str(doc.review_due_date) if doc.review_due_date else None}

        result.append({
            "document_type": req.document_type,
            "description": req.description,
            "iso_clause": req.iso_clause,
            "mandatory": req.mandatory,
            "notes": req.notes,
            "traffic_light": traffic,
            "document": doc_info,
        })

    return result
