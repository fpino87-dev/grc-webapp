from django.core.exceptions import ValidationError
from django.utils import timezone

from core.audit import log_action

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


def advance_phase(cycle, user, phase_notes: str = "", evidence=None, outcome: str = "") -> PdcaCycle:
    """
    Avanza la fase del ciclo PDCA validando i prerequisiti.
    Ogni transizione ha requisiti obbligatori.
    """
    if cycle.fase_corrente == "chiuso":
        raise ValidationError("Il ciclo è già chiuso.")

    current = cycle.fase_corrente

    # Valida prerequisiti per la fase corrente
    if current == "plan":
        if not phase_notes or len(phase_notes.strip()) < 20:
            raise ValidationError(
                "Per avanzare da PLAN a DO è obbligatorio descrivere "
                "l'azione pianificata (minimo 20 caratteri)."
            )
    elif current == "do":
        if evidence is None:
            raise ValidationError(
                "Per avanzare da DO a CHECK è obbligatorio "
                "allegare un'evidenza dell'implementazione."
            )
    elif current == "check":
        if not phase_notes or len(phase_notes.strip()) < 10:
            raise ValidationError(
                "Per avanzare da CHECK ad ACT è obbligatorio "
                "descrivere il risultato della verifica."
            )
        if outcome not in ("ok", "partial", "ko"):
            raise ValidationError(
                "Per avanzare da CHECK ad ACT è obbligatorio "
                "indicare l'esito: ok / partial / ko."
            )

    # Aggiorna la fase corrente con i dati inseriti
    phase_obj = cycle.phases.filter(phase=current).first()
    if phase_obj:
        if phase_notes:
            phase_obj.notes = phase_notes
        if evidence is not None:
            phase_obj.evidence = evidence
        if outcome:
            phase_obj.outcome = outcome
        phase_obj.completed_at = timezone.now()
        phase_obj.completed_by = user
        phase_obj.save()

    # Determina la fase successiva
    next_phase_map = {
        "plan": "do",
        "do": "check",
        "check": "act",
    }
    next_phase = next_phase_map.get(current)
    if not next_phase:
        raise ValidationError("Usa close_cycle() per chiudere dalla fase ACT.")

    cycle.fase_corrente = next_phase

    # Se CHECK = ko → salva esito e preparati a riaprire
    if current == "check" and outcome == "ko":
        cycle.check_outcome = "ko"

    cycle.save(update_fields=["fase_corrente", "check_outcome", "updated_at"])

    log_action(
        user=user,
        action_code="pdca.phase_advanced",
        level="L2",
        entity=cycle,
        payload={
            "from_phase": current,
            "to_phase": next_phase,
            "outcome": outcome or None,
            "has_evidence": evidence is not None,
        },
    )

    # Se CHECK = ko → apre automaticamente nuovo ciclo PLAN
    if current == "check" and outcome == "ko":
        new_cycle = create_cycle(
            plant=cycle.plant,
            title=f"[Riciclo] {cycle.title}",
            trigger_type="pdca_ko",
            trigger_source_id=cycle.pk,
        )
        cycle.reopened_as = new_cycle
        cycle.save(update_fields=["reopened_as"])
        log_action(
            user=user,
            action_code="pdca.cycle.reopened",
            level="L2",
            entity=new_cycle,
            payload={"original_cycle": str(cycle.pk)},
        )

    return cycle


def close_cycle(cycle, user, act_description: str = "") -> PdcaCycle:
    """
    Chiude il ciclo dalla fase ACT.
    Richiede descrizione standardizzazione.
    """
    if cycle.fase_corrente != "act":
        raise ValidationError(
            f"Il ciclo è in fase {cycle.fase_corrente}. "
            "Avanza fino ad ACT prima di chiudere."
        )
    if not act_description or len(act_description.strip()) < 20:
        raise ValidationError(
            "Per chiudere il ciclo è obbligatorio descrivere "
            "l'azione standardizzata (minimo 20 caratteri)."
        )

    cycle.fase_corrente = "chiuso"
    cycle.act_description = act_description
    cycle.closed_at = timezone.now()
    cycle.closed_by = user
    cycle.save(
        update_fields=[
            "fase_corrente",
            "act_description",
            "closed_at",
            "closed_by",
            "updated_at",
        ]
    )

    # Aggiorna modulo sorgente
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

    # Crea Lesson Learned automatica
    from apps.lessons.models import LessonLearned

    LessonLearned.objects.create(
        plant=cycle.plant,
        title=f"[PDCA] {cycle.title}",
        source_module="M11",
        source_id=cycle.pk,
        description=act_description,
        created_by=user,
        identified_by=user,
    )

    log_action(
        user=user,
        action_code="pdca.cycle.closed",
        level="L2",
        entity=cycle,
        payload={
            "trigger_type": cycle.trigger_type,
            "act_description": act_description[:100],
            "check_outcome": cycle.check_outcome,
        },
    )
    return cycle


