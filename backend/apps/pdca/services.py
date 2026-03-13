from .models import PdcaCycle, PdcaPhase


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
    for fase in ["plan", "do", "check", "act"]:
        PdcaPhase.objects.create(cycle=cycle, phase=fase)
    return cycle

