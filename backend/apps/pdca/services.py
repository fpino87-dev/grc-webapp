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

