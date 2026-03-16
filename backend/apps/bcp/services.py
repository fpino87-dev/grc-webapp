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


def record_test(
    plan: BcpPlan,
    result: str,
    user,
    notes: str = "",
    test_type: str = "tabletop",
    objectives: list | None = None,
    rto_achieved: int | None = None,
    rpo_achieved: int | None = None,
    participants_count: int = 0,
) -> tuple:
    """
    Record a BCP test and update last_test_date on the plan.
    Returns (BcpTest, list[str]) — the test instance and any warning messages.
    """
    from django.utils import timezone

    test = BcpTest.objects.create(
        plan=plan,
        test_date=timezone.now().date(),
        result=result,
        conducted_by=user,
        notes=notes,
        created_by=user,
        test_type=test_type,
        objectives=objectives or [],
        rto_achieved_hours=rto_achieved,
        rpo_achieved_hours=rpo_achieved,
        participants_count=participants_count,
    )
    plan.last_test_date = test.test_date
    try:
        from apps.compliance_schedule.services import get_due_date
        plan.next_test_date = get_due_date("bcp_test", plant=plan.plant, from_date=test.test_date)
        plan.save(update_fields=["last_test_date", "next_test_date", "updated_at"])
    except Exception:
        plan.save(update_fields=["last_test_date", "updated_at"])
    log_action(
        user=user,
        action_code="bcp.plan.test",
        level="L2",
        entity=plan,
        payload={
            "id": str(plan.id),
            "result": result,
            "test_id": str(test.id),
            "test_type": test_type,
            "rto_achieved": rto_achieved,
            "rpo_achieved": rpo_achieved,
        },
    )

    warnings = []

    # Compare achieved RTO/RPO against linked critical process targets
    linked_process = (
        plan.critical_process
        if plan.critical_process_id
        else plan.critical_processes.filter(deleted_at__isnull=True).first()
    )
    if linked_process is not None:
        if rto_achieved is not None and linked_process.mtpd_hours is not None:
            if rto_achieved > linked_process.mtpd_hours:
                warnings.append(
                    f"RTO raggiunto ({rto_achieved}h) supera MTPD del processo "
                    f"'{linked_process.name}' ({linked_process.mtpd_hours}h)"
                )
        if rto_achieved is not None and linked_process.rto_target_hours is not None:
            if rto_achieved > linked_process.rto_target_hours:
                warnings.append(
                    f"RTO raggiunto ({rto_achieved}h) supera RTO target "
                    f"({linked_process.rto_target_hours}h)"
                )

    # Se fallito o parziale crea PDCA automatico
    if result in ("fallito", "parziale"):
        from apps.pdca.services import create_cycle

        create_cycle(
            plant=plan.plant,
            title=f"PDCA BCP test {result} — {plan.title}",
            trigger_type="bcp_test_fallito",
            trigger_source_id=test.pk,
        )
        # notifica configurabile per test BCP fallito/parziale
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification(
                "bcp_test_failed",
                plant=plan.plant,
                context={"plan": plan},
            )
        except Exception:
            pass

    # Se RTO sforato crea anche PDCA autonomo
    if warnings and result == "superato":
        from apps.pdca.services import create_cycle
        create_cycle(
            plant=plan.plant,
            title=f"PDCA BCP RTO/MTPD sforato — {plan.title}",
            trigger_type="bcp_rto_sforato",
            trigger_source_id=test.pk,
        )

    return test, warnings
