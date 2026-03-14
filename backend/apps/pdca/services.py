from .models import PdcaCycle, PdcaPhase

PHASE_ORDER = ["plan", "do", "check", "act"]


def create_cycle(plant, title, trigger_type, trigger_source_id=None, scope_type="custom", scope_id=None):
    cycle = PdcaCycle.objects.create(
        plant=plant,
        title=title,
        trigger_type=trigger_type,
        trigger_source_id=trigger_source_id,
        scope_type=scope_type,
        scope_id=scope_id,
        # Incidente → salta direttamente ad ACT
        fase_corrente="act" if trigger_type == "incidente" else "plan",
    )
    for fase in PHASE_ORDER:
        PdcaPhase.objects.create(cycle=cycle, phase=fase)
    return cycle


def advance_phase(cycle, user):
    """Advance fase_corrente to the next phase in PLAN→DO→CHECK→ACT order.
    If already on ACT, marks cycle as completed (fase_corrente='completato'
    is not a valid choice, so we keep it at 'act' and log the completion).
    """
    from core.audit import log_action

    current_index = PHASE_ORDER.index(cycle.fase_corrente) if cycle.fase_corrente in PHASE_ORDER else -1
    next_index = current_index + 1

    if next_index < len(PHASE_ORDER):
        cycle.fase_corrente = PHASE_ORDER[next_index]
        cycle.save(update_fields=["fase_corrente", "updated_at"])
    # If already at last phase, nothing to advance — log anyway

    log_action(
        user=user,
        action_code="pdca.phase_advanced",
        level="L2",
        entity=cycle,
        payload={"cycle_id": str(cycle.pk), "fase_corrente": cycle.fase_corrente},
    )


def close_cycle(cycle, user):
    """Chiude il ciclo PDCA e aggiorna il modulo sorgente."""
    from django.utils import timezone
    from core.audit import log_action

    cycle.fase_corrente = "chiuso"
    cycle.closed_at = timezone.now()
    cycle.closed_by = user
    cycle.save(update_fields=["fase_corrente", "closed_at", "closed_by", "updated_at"])

    # Aggiorna il modulo sorgente
    if cycle.trigger_type == "risk_rosso":
        from apps.risk.models import RiskAssessment
        ra = RiskAssessment.objects.filter(pk=cycle.trigger_source_id).first()
        if ra:
            ra.risk_accepted = True
            ra.save(update_fields=["risk_accepted", "updated_at"])

    if cycle.trigger_type == "gap_controllo":
        from apps.controls.models import ControlInstance
        ci = ControlInstance.objects.filter(pk=cycle.trigger_source_id).first()
        if ci:
            ci.status = "parziale"
            ci.save(update_fields=["status", "updated_at"])

    # Crea automaticamente Lesson Learned
    from apps.lessons.models import LessonLearned
    LessonLearned.objects.create(
        plant=cycle.plant,
        title=f"[PDCA] {cycle.title}",
        source_module="M11",
        source_id=cycle.pk,
        description=cycle.act_description or "",
        created_by=user,
    )

    log_action(
        user=user,
        action_code="pdca.cycle.closed",
        level="L2",
        entity=cycle,
        payload={
            "trigger_type": cycle.trigger_type,
            "trigger_source_id": str(cycle.trigger_source_id),
        },
    )
    return cycle

