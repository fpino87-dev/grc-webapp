from .models import Control, ControlInstance


def evaluate_control(instance, new_status, user, note=""):
    from django.core.exceptions import ValidationError
    from django.utils import timezone

    from core.audit import log_action

    # HARD BLOCK: compliant e parziale richiedono evidenza valida
    if new_status in ("compliant", "parziale"):
        today = timezone.now().date()
        valid_evidences = instance.evidences.filter(
            valid_until__gte=today,
            deleted_at__isnull=True,
        )
        if not valid_evidences.exists():
            raise ValidationError(
                "Impossibile impostare lo stato a '{}' senza almeno "
                "un'evidenza valida collegata. "
                "Carica un'evidenza con data di validità futura.".format(new_status)
            )

    # HARD BLOCK: n/a richiede giustificazione scritta
    if new_status == "na":
        if not note or len(note.strip()) < 20:
            raise ValidationError(
                "Lo stato N/A richiede una giustificazione scritta "
                "di almeno 20 caratteri."
            )

    instance.status = new_status
    instance.last_evaluated_at = timezone.now()
    instance.last_evaluated_note = note
    instance.save(update_fields=[
        "status", "last_evaluated_at", "last_evaluated_note", "updated_at"
    ])

    log_action(
        user=user,
        action_code="control.evaluated",
        level="L2",
        entity=instance,
        payload={
            "new_status": new_status,
            "note": note,
            "evidences_count": instance.evidences.count(),
        },
    )
    return instance


def get_compliance_summary(plant_id, framework_code=None):
    qs = ControlInstance.objects.filter(plant_id=plant_id)
    if framework_code:
        qs = qs.filter(control__framework__code=framework_code)
    total = qs.count()
    if total == 0:
        return {"total": 0, "compliant": 0, "gap": 0, "parziale": 0, "na": 0, "non_valutato": 0, "pct_compliant": 0}
    from django.db.models import Count

    counts = qs.values("status").annotate(n=Count("id"))
    result = {r["status"]: r["n"] for r in counts}
    compliant = result.get("compliant", 0)
    return {
        "total": total,
        "compliant": compliant,
        "gap": result.get("gap", 0),
        "parziale": result.get("parziale", 0),
        "na": result.get("na", 0),
        "non_valutato": result.get("non_valutato", 0),
        "pct_compliant": round(compliant / total * 100, 1),
    }
