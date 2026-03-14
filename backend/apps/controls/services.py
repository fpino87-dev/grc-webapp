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


def gap_analysis(source_framework_code: str, target_framework_code: str, plant_id) -> dict:
    """
    Confronta due framework e mostra cosa manca per passare dall'uno all'altro.
    """
    from .models import Control, ControlInstance, ControlMapping

    target_controls = Control.objects.filter(
        framework__code=target_framework_code,
        deleted_at__isnull=True,
    ).prefetch_related("mappings_to__source_control")

    result = {
        "source_framework": source_framework_code,
        "target_framework": target_framework_code,
        "covered":    [],
        "partial":    [],
        "gap":        [],
        "not_mapped": [],
        "summary":    {},
    }

    for tc in target_controls:
        mappings = tc.mappings_to.filter(
            source_control__framework__code=source_framework_code
        )
        if not mappings.exists():
            result["not_mapped"].append({
                "id": str(tc.pk),
                "external_id": tc.external_id,
                "title": tc.get_title("it"),
                "domain": tc.domain.get_name("it") if tc.domain else "",
            })
            continue

        best_status = "non_valutato"
        for mapping in mappings:
            try:
                ci = ControlInstance.objects.get(
                    plant_id=plant_id,
                    control=mapping.source_control,
                )
                order = {"compliant": 4, "parziale": 3, "na": 2, "gap": 1, "non_valutato": 0}
                if order.get(ci.status, 0) > order.get(best_status, 0):
                    best_status = ci.status
            except ControlInstance.DoesNotExist:
                pass

        entry = {
            "id": str(tc.pk),
            "external_id": tc.external_id,
            "title": tc.get_title("it"),
            "domain": tc.domain.get_name("it") if tc.domain else "",
            "source_status": best_status,
        }
        if best_status == "compliant":
            result["covered"].append(entry)
        elif best_status == "parziale":
            result["partial"].append(entry)
        else:
            result["gap"].append(entry)

    total = target_controls.count()
    result["summary"] = {
        "total":      total,
        "covered":    len(result["covered"]),
        "partial":    len(result["partial"]),
        "gap":        len(result["gap"]),
        "not_mapped": len(result["not_mapped"]),
        "pct_ready":  round(len(result["covered"]) / total * 100, 1) if total else 0,
    }
    return result


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
