from django.utils import timezone
from core.audit import log_action
from .models import BcpPlan, BcpTest


def approve_plan(plan: BcpPlan, user) -> BcpPlan:
    """Transition a BCP plan from bozza to approvato."""
    plan.status = "approvato"
    plan.approved_by = user
    plan.approved_at = timezone.now()
    plan.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    log_action(
        user=user,
        action_code="bcp.plan.approve",
        level="L2",
        entity=plan,
        payload={"id": str(plan.id), "title": plan.title},
    )
    return plan


def check_missing_bcp_plans(plant):
    """Restituisce processi critici (criticality >= 4) senza BCP plan attivo."""
    from apps.bia.models import CriticalProcess

    processes = CriticalProcess.objects.filter(
        plant=plant,
        criticality__gte=4,
        status="approvato",
        deleted_at__isnull=True,
    )
    missing = []
    for p in processes:
        has_bcp = p.bcp_plans.filter(deleted_at__isnull=True).exists()
        if not has_bcp:
            missing.append(p)
    return missing


def record_test(plan: BcpPlan, result: str, user, notes: str = "") -> BcpTest:
    """Record a BCP test and update last_test_date on the plan."""
    from django.utils import timezone

    test = BcpTest.objects.create(
        plan=plan,
        test_date=timezone.now().date(),
        result=result,
        conducted_by=user,
        notes=notes,
        created_by=user,
    )
    plan.last_test_date = test.test_date
    plan.save(update_fields=["last_test_date", "updated_at"])
    log_action(
        user=user,
        action_code="bcp.plan.test",
        level="L2",
        entity=plan,
        payload={"id": str(plan.id), "result": result, "test_id": str(test.id)},
    )

    # Se fallito o parziale crea PDCA automatico
    if result in ("fallito", "parziale"):
        from apps.pdca.services import create_cycle
        create_cycle(
            plant=plan.plant,
            title=f"PDCA BCP test fallito — {plan.title}",
            trigger_type="bcp_test_fallito",
            trigger_source_id=test.pk,
        )

    return test
