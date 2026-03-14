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
    return test
