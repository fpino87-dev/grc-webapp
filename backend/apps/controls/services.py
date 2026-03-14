from .models import Control, ControlInstance


def evaluate_control(instance, status, user, notes=""):
    from django.utils import timezone

    from core.audit import log_action

    instance.status = status
    instance.notes = notes
    instance.last_evaluated_at = timezone.now()
    instance.save(update_fields=["status", "notes", "last_evaluated_at", "updated_at"])
    log_action(
        user=user,
        action_code=f"control_evaluated:{status}",
        level="L2",
        entity=instance,
        payload={"id": str(instance.id), "status": status},
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
