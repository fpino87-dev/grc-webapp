import datetime

from django.utils import timezone
from core.audit import log_action

from .models import AuditPrep, AuditFinding

DEADLINE_DAYS = {
    "major_nc":    30,
    "minor_nc":    90,
    "observation": 180,
    "opportunity": None,
}

_RULE_TYPE_MAP = {
    "major_nc":    "finding_major",
    "minor_nc":    "finding_minor",
    "observation": "finding_observation",
}

PDCA_TRIGGER_MAP = {
    "major_nc":    "finding_major",
    "minor_nc":    "finding_minor",
    "observation": "finding_observation",
    "opportunity": "finding_opportunity",
}


def calc_readiness_score(audit_prep: AuditPrep) -> int:
    """Calculate readiness score 0-100 based on evidence_items status."""
    items = list(audit_prep.evidence_items.all())
    if not items:
        return 0
    total = len(items)
    score = 0
    for item in items:
        if item.status == "presente":
            score += 1
        elif item.status == "scaduto":
            score += 0.5
    return round(score / total * 100)


def update_readiness_score(audit_prep: AuditPrep) -> AuditPrep:
    """Recalculate and persist the readiness_score field."""
    audit_prep.readiness_score = calc_readiness_score(audit_prep)
    audit_prep.save(update_fields=["readiness_score", "updated_at"])
    return audit_prep


def open_finding(audit_prep, finding_type: str, title: str,
                 description: str, audit_date, user,
                 control_instance=None,
                 auditor_name: str = "") -> AuditFinding:
    """
    Crea un AuditFinding e genera automaticamente:
    - PDCA (obbligatorio per major/minor)
    - Scadenza risposta calcolata
    - Task se major NC
    """
    from apps.pdca.services import create_cycle

    deadline = None
    rule_type = _RULE_TYPE_MAP.get(finding_type)
    if rule_type:
        try:
            from apps.compliance_schedule.services import get_due_date
            base_date = audit_date if hasattr(audit_date, "year") else timezone.now().date()
            deadline = get_due_date(rule_type, plant=audit_prep.plant, from_date=base_date)
        except Exception:
            deadline_days = DEADLINE_DAYS.get(finding_type)
            if deadline_days:
                base_date = audit_date if hasattr(audit_date, "year") else timezone.now().date()
                deadline = base_date + datetime.timedelta(days=deadline_days)

    finding = AuditFinding.objects.create(
        audit_prep=audit_prep,
        control_instance=control_instance,
        finding_type=finding_type,
        title=title,
        description=description,
        auditor_name=auditor_name,
        audit_date=audit_date,
        response_deadline=deadline,
        status="open",
        created_by=user,
    )

    # Crea PDCA automatico per major e minor NC
    if finding_type in ("major_nc", "minor_nc"):
        cycle_title = f"[{finding_type.upper()}] {title}"
        cycle = create_cycle(
            plant=audit_prep.plant,
            title=cycle_title,
            trigger_type=PDCA_TRIGGER_MAP[finding_type],
            trigger_source_id=finding.pk,
            scope_type="finding",
            scope_id=finding.pk,
        )
        finding.pdca_cycle = cycle
        finding.save(update_fields=["pdca_cycle"])

    # Task urgente per major NC
    if finding_type == "major_nc":
        from apps.tasks.services import create_task
        create_task(
            plant=audit_prep.plant,
            title=f"MAJOR NC: {title}",
            description=(
                f"Non conformita' maggiore rilevata in audit.\n"
                f"Scadenza risposta: {deadline}\n\n{description}"
            ),
            priority="critica",
            source_module="M17",
            source_id=finding.pk,
            due_date=deadline,
            assign_type="role",
            assign_value="compliance_officer",
        )

    log_action(
        user=user,
        action_code="audit.finding.opened",
        level="L1" if finding_type == "major_nc" else "L2",
        entity=finding,
        payload={
            "finding_type": finding_type,
            "title": title[:100],
            "deadline": str(deadline) if deadline else None,
            "has_pdca": finding.pdca_cycle is not None,
        },
    )
    return finding


def close_finding(finding: AuditFinding, user,
                  closure_notes: str = "",
                  evidence=None) -> AuditFinding:
    """
    Chiude un AuditFinding.
    Richiede evidenza per major e minor NC.
    Crea automaticamente Lesson Learned.
    Aggiorna ControlInstance se collegato.
    """
    from django.core.exceptions import ValidationError

    if finding.finding_type in ("major_nc", "minor_nc"):
        if evidence is None:
            raise ValidationError(
                f"Per {finding.finding_type} e' obbligatoria "
                f"un'evidenza di chiusura."
            )
        if not closure_notes or len(closure_notes.strip()) < 20:
            raise ValidationError(
                "Le note di chiusura devono essere almeno 20 caratteri."
            )

    finding.status = "closed"
    finding.closure_notes = closure_notes
    finding.closure_evidence = evidence
    finding.closed_at = timezone.now()
    finding.closed_by = user
    finding.save(update_fields=[
        "status", "closure_notes", "closure_evidence",
        "closed_at", "closed_by", "updated_at",
    ])

    # Aggiorna ControlInstance se collegato
    if finding.control_instance:
        ci = finding.control_instance
        if ci.status == "gap":
            ci.status = "parziale"
            ci.save(update_fields=["status", "updated_at"])

    # Chiudi PDCA collegato se esiste
    if finding.pdca_cycle and finding.pdca_cycle.fase_corrente != "chiuso":
        from apps.pdca.services import close_cycle
        close_cycle(finding.pdca_cycle, user)

    # Crea Lesson Learned automatica
    from apps.lessons.models import LessonLearned
    ll = LessonLearned.objects.create(
        plant=finding.audit_prep.plant,
        title=f"[Finding] {finding.title}",
        description=(
            f"Tipo: {finding.finding_type}\n"
            f"Auditor: {finding.auditor_name}\n"
            f"Causa radice: {finding.root_cause}\n"
            f"Azione correttiva: {finding.corrective_action}\n"
            f"Note chiusura: {closure_notes}"
        ),
        category="audit",
        source_module="M17",
        source_id=finding.pk,
        created_by=user,
    )
    finding.lesson_learned = ll
    finding.save(update_fields=["lesson_learned"])

    log_action(
        user=user,
        action_code="audit.finding.closed",
        level="L1" if finding.finding_type == "major_nc" else "L2",
        entity=finding,
        payload={
            "finding_type": finding.finding_type,
            "has_evidence": evidence is not None,
            "lesson_id": str(ll.pk),
        },
    )
    return finding
