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
    from .models import BcpPlan

    processes = CriticalProcess.objects.filter(
        plant=plant,
        criticality__gte=4,
        status="approvato",
        deleted_at__isnull=True,
    )
    missing = []
    for p in processes:
        has_direct_bcp = p.bcp_plans.filter(deleted_at__isnull=True).exists()
        has_m2m_bcp = BcpPlan.objects.filter(
            deleted_at__isnull=True,
            critical_processes=p,
        ).exists()
        has_bcp = has_direct_bcp or has_m2m_bcp
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
    evidence_ids: list | None = None,
    evidence_file=None,
    evidence_payload: dict | None = None,
) -> tuple:
    """
    Record a BCP test and update last_test_date on the plan.
    Returns (BcpTest, list[str]) — the test instance and any warning messages.
    """
    from django.utils import timezone
    from django.core.exceptions import ValidationError

    if plan.status == "approvato":
        raise ValidationError("Impossibile registrare un test su un piano BCP approvato.")

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

    # Calcolo prossima scadenza test BCP: dipende dalle impostazioni del singolo piano.
    def _add_duration(base, value: int, unit: str):
        import datetime as _dt

        if unit == "days":
            return base + _dt.timedelta(days=value)
        if unit == "weeks":
            return base + _dt.timedelta(weeks=value)
        if unit == "months":
            month = base.month - 1 + value
            year = base.year + month // 12
            month = month % 12 + 1
            day = min(
                base.day,
                [31, 28, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month],
            )
            return _dt.date(year, month, day)
        if unit == "years":
            try:
                return base.replace(year=base.year + value)
            except ValueError:
                return base.replace(year=base.year + value, day=28)
        # Fallback: approssimazione
        return base + _dt.timedelta(days=value * 30)

    try:
        value = plan.test_frequency_value or 1
        unit = plan.test_frequency_unit or "years"
        plan.next_test_date = _add_duration(test.test_date, value, unit)
        plan.save(update_fields=["last_test_date", "next_test_date", "updated_at"])
    except Exception:
        plan.save(update_fields=["last_test_date", "updated_at"])

    try:
        from apps.documents.models import Evidence

        evidence_ids = evidence_ids or []
        if evidence_ids:
            existing_evidences = Evidence.objects.filter(
                pk__in=evidence_ids,
                deleted_at__isnull=True,
            )
            test.evidences.add(*list(existing_evidences))

        if evidence_file:
            from apps.documents.services import create_evidence_with_file

            payload = evidence_payload.copy() if evidence_payload else {}
            payload.setdefault("title", f"BCP test — {plan.title}")
            payload.setdefault("evidence_type", "test_result")
            payload.setdefault("description", notes or payload.get("description", ""))
            payload.setdefault("plant", str(plan.plant_id) if plan.plant_id else None)
            if plan.next_test_date:
                payload.setdefault("valid_until", plan.next_test_date.isoformat())

            created_ev = create_evidence_with_file(payload, evidence_file, user)
            test.evidences.add(created_ev)
    except Exception:
        # le evidenze non devono bloccare la registrazione del test
        pass
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


def delete_bcp_plan(plan: BcpPlan, user) -> None:
    """Soft delete del piano BCP e dei test associati."""
    from core.audit import log_action

    for test in plan.tests.all():
        test.soft_delete()
        log_action(
            user=user,
            action_code="bcp.test.deleted",
            level="L2",
            entity=test,
            payload={"id": str(test.id), "result": test.result},
        )

    plan.soft_delete()
    log_action(
        user=user,
        action_code="bcp.plan.deleted",
        level="L2",
        entity=plan,
        payload={"id": str(plan.id), "title": plan.title},
    )
