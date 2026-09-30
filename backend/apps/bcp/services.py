import datetime
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action
from .models import BcpPlan, BcpTest

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# Regole uniche del modulo
#
# Approvazione del piano e prova della sua efficacia sono due stati separati:
#   - `status` (bozza / approvato / archiviato) dice se il piano è in vigore;
#   - lo stato del test (`plan_test_state`) dice se l'efficacia è dimostrata.
# Un test scaduto non toglie l'approvazione: il processo risulta "scoperto per
# test scaduto" (giallo), non "senza piano".
# ───────────────────────────────────────────────────────────────────────────

# Processo critico: criticità BIA ≥ 4, qualunque sia lo stato della BIA.
CRITICAL_PROCESS_MIN_CRITICALITY = 4

TEST_OK = "ok"
TEST_OVERDUE = "overdue"
TEST_NEVER = "never"

COVERED = "covered"
TEST_EXPIRED = "test_expired"
MISSING = "missing"


def add_duration(base: datetime.date, value: int, unit: str) -> datetime.date:
    """Data `base` spostata avanti di `value` giorni/settimane/mesi/anni."""
    if unit == "days":
        return base + datetime.timedelta(days=value)
    if unit == "weeks":
        return base + datetime.timedelta(weeks=value)
    if unit == "months":
        month = base.month - 1 + value
        year = base.year + month // 12
        month = month % 12 + 1
        last_day = [31, 29 if _is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
        return datetime.date(year, month, min(base.day, last_day))
    try:
        return base.replace(year=base.year + value)
    except ValueError:  # 29 febbraio
        return base.replace(year=base.year + value, day=28)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _plant_today(plant):
    from apps.plants.services import plant_today

    return plant_today(plant)


def plan_test_state(last_test_date, next_test_date, today) -> str:
    """Stato del test di un piano: mai testato, scaduto o in regola."""
    if last_test_date is None:
        return TEST_NEVER
    if next_test_date is None or next_test_date < today:
        return TEST_OVERDUE
    return TEST_OK


def recompute_next_test_date(plan: BcpPlan) -> None:
    """Prossimo test = ultimo test + frequenza del piano (non salva)."""
    if plan.last_test_date is None:
        plan.next_test_date = None
        return
    plan.next_test_date = add_duration(
        plan.last_test_date,
        plan.test_frequency_value or 1,
        plan.test_frequency_unit or "years",
    )


def _plans_covering(process_ids):
    """Piani (non eliminati) collegati ai processi, con l'insieme dei processi
    coperti da ciascuno: FK storico ∪ elenco."""
    process_ids = list(process_ids)
    plans = (
        BcpPlan.objects.filter(deleted_at__isnull=True)
        .filter(Q(critical_process_id__in=process_ids) | Q(critical_processes__in=process_ids))
        .distinct()
        .select_related("plant")
    )
    links = {}
    for pid, plan_id in BcpPlan.critical_processes.through.objects.filter(
        criticalprocess_id__in=process_ids, bcpplan__in=plans,
    ).values_list("criticalprocess_id", "bcpplan_id"):
        links.setdefault(plan_id, set()).add(pid)
    result = []
    for plan in plans:
        covered = set(links.get(plan.pk, set()))
        if plan.critical_process_id in process_ids:
            covered.add(plan.critical_process_id)
        result.append((plan, covered))
    return result


def process_coverage(process_ids) -> dict:
    """Stato di copertura BCP per processo: `covered` (piano approvato con
    test in regola), `test_expired` (piano approvato ma test scaduto o mai
    eseguito). I processi assenti dal risultato non hanno un piano approvato.

    Regola unica usata da modulo BCP, Reporting e riesame (M13)."""
    process_ids = list(process_ids)
    if not process_ids:
        return {}
    today_by_plant = {}
    coverage = {}
    for plan, covered in _plans_covering(process_ids):
        if plan.status != "approvato":
            continue
        if plan.plant_id not in today_by_plant:
            today_by_plant[plan.plant_id] = _plant_today(plan.plant)
        state = plan_test_state(plan.last_test_date, plan.next_test_date, today_by_plant[plan.plant_id])
        value = COVERED if state == TEST_OK else TEST_EXPIRED
        for pid in covered:
            if coverage.get(pid) != COVERED:
                coverage[pid] = value
    return coverage


def processes_with_approved_bcp(process_ids) -> set:
    """ID dei processi coperti da almeno un piano BCP **approvato** (anche con
    test scaduto). Bozze e piani archiviati non coprono."""
    return set(process_coverage(process_ids))


def _critical(processes_qs):
    return list(
        processes_qs.filter(
            deleted_at__isnull=True, criticality__gte=CRITICAL_PROCESS_MIN_CRITICALITY,
        ).order_by("-criticality", "name")
    )


def critical_processes_without_bcp(processes_qs):
    """Processi critici del queryset senza un piano BCP approvato, ordinati per
    criticità e nome."""
    critical = _critical(processes_qs)
    coverage = process_coverage(p.pk for p in critical)
    return [p for p in critical if p.pk not in coverage]


def critical_processes_test_expired(processes_qs):
    """Processi critici con un piano approvato ma nessun test in regola:
    scoperti per test scaduto o mai eseguito."""
    critical = _critical(processes_qs)
    coverage = process_coverage(p.pk for p in critical)
    return [p for p in critical if coverage.get(p.pk) == TEST_EXPIRED]


def check_missing_bcp_plans(plant):
    """Processi critici del sito senza un piano BCP approvato."""
    from apps.bia.models import CriticalProcess

    return critical_processes_without_bcp(CriticalProcess.objects.filter(plant=plant))


def demonstrated_rto(plan: BcpPlan):
    """RTO che il piano sa garantire: quello ottenuto nell'ultimo test che lo
    ha misurato; senza test misurati, quello dichiarato nel piano."""
    measured = (
        plan.tests.filter(deleted_at__isnull=True, rto_achieved_hours__isnull=False)
        .order_by("-test_date", "-created_at")
        .values_list("rto_achieved_hours", flat=True)
        .first()
    )
    return measured if measured is not None else plan.rto_hours


def coverage_rows(processes_qs) -> list[dict]:
    """Processi critici con stato di copertura e piani collegati, per la
    vista Copertura del modulo BCP."""
    critical = list(
        processes_qs.filter(
            deleted_at__isnull=True, criticality__gte=CRITICAL_PROCESS_MIN_CRITICALITY,
        ).select_related("plant").order_by("-criticality", "name")
    )
    ids = [p.pk for p in critical]
    coverage = process_coverage(ids)
    plans_by_proc = {}
    plan_list = _plans_covering(ids)
    last_by_plan = {}
    for t in (
        BcpTest.objects.filter(plan__in=[p for p, _c in plan_list], deleted_at__isnull=True)
        .order_by("plan_id", "-test_date", "-created_at")
        .values("plan_id", "test_date", "result", "rto_achieved_hours", "rpo_achieved_hours")
    ):
        last_by_plan.setdefault(t["plan_id"], t)
    measured_rto = {}
    for t in (
        BcpTest.objects.filter(
            plan__in=[p for p, _c in plan_list], deleted_at__isnull=True,
            rto_achieved_hours__isnull=False,
        ).order_by("plan_id", "-test_date", "-created_at").values("plan_id", "rto_achieved_hours")
    ):
        measured_rto.setdefault(t["plan_id"], t["rto_achieved_hours"])
    today_by_plant = {}
    for plan, covered in plan_list:
        if plan.status == "archiviato":
            continue
        if plan.plant_id not in today_by_plant:
            today_by_plant[plan.plant_id] = _plant_today(plan.plant)
        last = last_by_plan.get(plan.pk)
        entry = {
            "id": str(plan.pk),
            "title": plan.title,
            "status": plan.status,
            "test_state": plan_test_state(
                plan.last_test_date, plan.next_test_date, today_by_plant[plan.plant_id],
            ),
            "last_test_date": plan.last_test_date.isoformat() if plan.last_test_date else None,
            "next_test_date": plan.next_test_date.isoformat() if plan.next_test_date else None,
            "last_test_result": last["result"] if last else None,
            "rto_declared": plan.rto_hours,
            "rto_demonstrated": measured_rto.get(plan.pk, plan.rto_hours),
            "rto_measured": plan.pk in measured_rto,
        }
        for pid in covered:
            plans_by_proc.setdefault(pid, []).append(entry)
    rows = []
    for proc in critical:
        rows.append({
            "process_id": str(proc.pk),
            "process_name": proc.name,
            "plant": str(proc.plant_id) if proc.plant_id else None,
            "criticality": proc.criticality,
            "rto_target_hours": proc.rto_target_hours,
            "rpo_target_hours": proc.rpo_target_hours,
            "mtpd_hours": proc.mtpd_hours,
            "coverage": coverage.get(proc.pk, MISSING),
            "plans": sorted(
                plans_by_proc.get(proc.pk, []),
                key=lambda e: (e["status"] != "approvato", e["title"]),
            ),
        })
    return rows


# ───────────────────────────────────────────────────────────────────────────
# Piano
# ───────────────────────────────────────────────────────────────────────────

def set_plan_processes(plan: BcpPlan, process_ids) -> None:
    """Imposta i processi coperti dal piano. Devono essere processi BIA del
    sito del piano. Il FK storico viene azzerato: l'elenco è l'unica fonte."""
    from apps.bia.models import CriticalProcess

    process_ids = [pid for pid in (process_ids or []) if pid]
    processes = list(
        CriticalProcess.objects.filter(pk__in=process_ids, deleted_at__isnull=True)
    )
    if len(processes) != len(set(str(p) for p in process_ids)):
        raise ValidationError(_("Uno o più processi indicati non esistono."))
    if any(p.plant_id != plan.plant_id for p in processes):
        raise ValidationError(_("I processi coperti devono appartenere al sito del piano."))
    plan.critical_processes.set(processes)
    if plan.critical_process_id:
        plan.critical_process = None
        plan.save(update_fields=["critical_process", "updated_at"])


def validate_plan_document(plan_plant_id, document) -> None:
    """Il documento del piano deve essere visibile dal sito del piano: del sito,
    di organizzazione o condiviso con il sito."""
    if document is None:
        return
    if document.plant_id in (None, plan_plant_id):
        return
    if document.shared_plants.filter(pk=plan_plant_id).exists():
        return
    raise ValidationError(_("Il documento scelto non è disponibile per il sito del piano."))


@transaction.atomic
def save_plan(plan: BcpPlan, user, *, created: bool, process_ids=None, frequency_changed=False) -> BcpPlan:
    """Completa creazione/modifica del piano dopo il salvataggio del serializer:
    processi coperti, prossima scadenza del test e audit."""
    if process_ids is not None:
        set_plan_processes(plan, process_ids)
    elif plan.critical_process_id:
        # client storici (es. wizard rischio) che indicano il solo FK: il
        # processo si aggiunge all'elenco
        set_plan_processes(
            plan,
            [*plan.critical_processes.values_list("pk", flat=True), plan.critical_process_id],
        )
    if frequency_changed and plan.last_test_date:
        recompute_next_test_date(plan)
        plan.save(update_fields=["next_test_date", "updated_at"])
    log_action(
        user=user,
        action_code="bcp.plan.create" if created else "bcp.plan.update",
        level="L2",
        entity=plan,
        payload={
            "id": str(plan.id),
            "title": plan.title,
            "document_id": str(plan.document_id) if plan.document_id else None,
            "processes": plan.critical_processes.count(),
        },
    )
    return plan


def approvable_plant_ids(user):
    """Siti su cui l'utente può approvare piani BCP: `None` = tutti.

    Approva il Compliance Officer (ruolo operativo, "CISO di sito") sul proprio
    perimetro, oppure chi ha la nomina governance CISO in vigore sullo stesso
    perimetro (organizzazione, BU o sito)."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.governance.models import NormativeRole, RoleAssignment
    from apps.plants.models import Plant

    if user is None or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return None

    allowed = set()
    accesses = UserPlantAccess.objects.filter(
        user=user, role=GrcRole.COMPLIANCE_OFFICER, deleted_at__isnull=True,
    ).prefetch_related("scope_plants")
    for access in accesses:
        if access.scope_type == "org":
            return None
        if access.scope_type == "bu" and access.scope_bu_id:
            allowed.update(Plant.objects.filter(bu_id=access.scope_bu_id).values_list("pk", flat=True))
        else:
            allowed.update(p.pk for p in access.scope_plants.all())

    today = timezone.localdate()
    nominations = RoleAssignment.objects.filter(
        user=user, role=NormativeRole.CISO, deleted_at__isnull=True, valid_from__lte=today,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    for ra in nominations:
        if ra.scope_type == "org":
            return None
        if ra.scope_type == "bu" and ra.scope_id:
            allowed.update(Plant.objects.filter(bu_id=ra.scope_id).values_list("pk", flat=True))
        elif ra.scope_type == "plant" and ra.scope_id:
            allowed.add(ra.scope_id)
    return allowed


def can_approve_plan(user, plan: BcpPlan, allowed=...) -> bool:
    if allowed is ...:
        allowed = approvable_plant_ids(user)
    return allowed is None or plan.plant_id in allowed


def approve_plan(plan: BcpPlan, user) -> BcpPlan:
    """Porta un piano BCP da bozza ad approvato."""
    if plan.status != "bozza":
        raise ValidationError(_("Si approva solo un piano in bozza."))
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


def archive_plan(plan: BcpPlan, user) -> BcpPlan:
    """Archivia un piano non più in uso: resta consultabile con i suoi test
    ma non copre più nessun processo."""
    if plan.status == "archiviato":
        raise ValidationError(_("Il piano è già archiviato."))
    plan.status = "archiviato"
    plan.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action_code="bcp.plan.archive",
        level="L2",
        entity=plan,
        payload={"id": str(plan.id), "title": plan.title},
    )
    return plan


# ───────────────────────────────────────────────────────────────────────────
# Test
# ───────────────────────────────────────────────────────────────────────────

def _target_warnings(plan: BcpPlan, rto_achieved, rpo_achieved) -> list[dict]:
    """Confronto dei tempi ottenuti nel test con i target BIA di ogni processo
    coperto dal piano."""
    from apps.bia.models import CriticalProcess

    processes = CriticalProcess.objects.filter(
        Q(pk__in=plan.critical_processes.values("pk")) | Q(pk=plan.critical_process_id),
        deleted_at__isnull=True,
    ).order_by("name")
    warnings = []
    for proc in processes:
        checks = [
            ("rto_over_mtpd", rto_achieved, proc.mtpd_hours),
            ("rto_over_target", rto_achieved, proc.rto_target_hours),
            ("rpo_over_target", rpo_achieved, proc.rpo_target_hours),
        ]
        for code, achieved, target in checks:
            if achieved is not None and target is not None and achieved > target:
                warnings.append({
                    "code": code, "process": proc.name, "achieved": achieved, "target": target,
                })
    return warnings


@transaction.atomic
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
    test_date: datetime.date | None = None,
) -> tuple:
    """Registra un test del piano (bozza o approvato) e aggiorna la scadenza.

    Il test non tocca l'approvazione. Esito fallito/parziale → PDCA e notifica;
    esito superato ma tempi oltre i target BIA → PDCA di sforamento.
    Ritorna (BcpTest, list[dict]) con gli avvisi sui target.
    """
    if plan.status == "archiviato":
        raise ValidationError(_("Un piano archiviato non si testa."))
    if result not in dict(BcpTest.RESULT_CHOICES):
        raise ValidationError(_("Esito del test non valido."))
    if test_type not in dict(BcpTest.TEST_TYPE_CHOICES):
        raise ValidationError(_("Tipo di test non valido."))
    today = _plant_today(plan.plant)
    test_date = test_date or today
    if test_date > today:
        raise ValidationError(_("La data del test non può essere futura."))
    # Evidenze verificate PRIMA di salvare il test: un file non ammesso o
    # un'evidenza fuori sito blocca la registrazione invece di perdersi.
    existing_evidences = _evidences_for_plan(plan, evidence_ids)
    if evidence_file:
        from core.uploads import validate_uploaded_file

        validate_uploaded_file(evidence_file)

    test = BcpTest.objects.create(
        plan=plan,
        test_date=test_date,
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
    # Un test registrato a posteriori, più vecchio dell'ultimo, non sposta la scadenza.
    if plan.last_test_date is None or test_date >= plan.last_test_date:
        plan.last_test_date = test_date
        recompute_next_test_date(plan)
        plan.save(update_fields=["last_test_date", "next_test_date", "updated_at"])

    _link_evidences(test, user, existing_evidences, evidence_file, evidence_payload, notes)

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
            "test_date": test_date.isoformat(),
            "rto_achieved": rto_achieved,
            "rpo_achieved": rpo_achieved,
            "evidences": test.evidences.count(),
        },
    )

    warnings = _target_warnings(plan, rto_achieved, rpo_achieved)

    from apps.pdca.services import create_cycle

    if result in ("fallito", "parziale"):
        create_cycle(
            plant=plan.plant,
            title=f"PDCA BCP test {result} — {plan.title}",
            trigger_type="bcp_test_fallito",
            trigger_source_id=test.pk,
        )
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification("bcp_test_failed", plant=plan.plant, context={"plan": plan})
        except Exception as exc:
            logger.warning("BCP: notifica test fallito non inviata per piano %s: %s", plan.pk, exc)
    elif warnings:
        create_cycle(
            plant=plan.plant,
            title=f"PDCA BCP RTO/RPO sforato — {plan.title}",
            trigger_type="bcp_rto_sforato",
            trigger_source_id=test.pk,
        )

    return test, warnings


def _evidences_for_plan(plan: BcpPlan, evidence_ids) -> list:
    """Evidenze esistenti collegabili a un test del piano: non eliminate e del
    sito del piano, di organizzazione o condivise con il sito (le stesse che
    l'elenco evidenze mostra per quel sito)."""
    from apps.documents.models import Evidence
    from apps.documents.services import evidence_available_to_plant_q

    ids = {str(e) for e in (evidence_ids or []) if e}
    if not ids:
        return []
    evidences = list(
        Evidence.objects.filter(pk__in=ids, deleted_at__isnull=True)
        .filter(evidence_available_to_plant_q(plan.plant_id))
        .distinct()
    )
    if len(evidences) != len(ids):
        raise ValidationError(_("Una o più evidenze indicate non esistono o non sono del sito del piano."))
    return evidences


def _link_evidences(test: BcpTest, user, evidences, evidence_file, evidence_payload=None, notes="") -> int:
    """Collega al test evidenze esistenti e/o una nuova evidenza dal file
    caricato (tipo "Risultato test", valida fino al prossimo test del piano).
    Ritorna il numero di evidenze aggiunte."""
    plan = test.plan
    added = list(evidences)
    if evidence_file:
        from apps.documents.services import create_evidence_with_file

        payload = evidence_payload.copy() if evidence_payload else {}
        payload.setdefault("title", f"BCP test {test.test_date.isoformat()} — {plan.title}"[:300])
        payload.setdefault("evidence_type", "test_result")
        payload.setdefault("description", notes or "")
        payload.setdefault("plant", str(plan.plant_id) if plan.plant_id else None)
        if plan.next_test_date:
            payload.setdefault("valid_until", plan.next_test_date.isoformat())
        added.append(create_evidence_with_file(payload, evidence_file, user))
    already = set(test.evidences.values_list("pk", flat=True))
    new = [e for e in added if e.pk not in already]
    if new:
        test.evidences.add(*new)
    return len(new)


@transaction.atomic
def add_test_evidences(test: BcpTest, user, evidence_ids=None, evidence_file=None) -> int:
    """Aggiunge evidenze a un test già registrato (le evidenze si aggiungono,
    esito e tempi del test restano quelli registrati)."""
    if not evidence_ids and not evidence_file:
        raise ValidationError(_("Indica un file o almeno un'evidenza esistente."))
    evidences = _evidences_for_plan(test.plan, evidence_ids)
    if evidence_file:
        from core.uploads import validate_uploaded_file

        validate_uploaded_file(evidence_file)
    added = _link_evidences(test, user, evidences, evidence_file)
    log_action(
        user=user,
        action_code="bcp.test.evidence_added",
        level="L2",
        entity=test,
        payload={"id": str(test.id), "plan_id": str(test.plan_id), "added": added},
    )
    return added


def delete_test(test: BcpTest, user) -> None:
    """Elimina (soft) un test e riallinea ultima/prossima data del piano."""
    plan = test.plan
    test.soft_delete()
    log_action(
        user=user,
        action_code="bcp.test.deleted",
        level="L2",
        entity=test,
        payload={"id": str(test.id), "plan_id": str(test.plan_id)},
    )
    last = (
        plan.tests.filter(deleted_at__isnull=True)
        .order_by("-test_date").values_list("test_date", flat=True).first()
    )
    plan.last_test_date = last
    recompute_next_test_date(plan)
    plan.save(update_fields=["last_test_date", "next_test_date", "updated_at"])


def delete_bcp_plan(plan: BcpPlan, user) -> None:
    """Soft delete del piano BCP e dei test associati."""
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


# ───────────────────────────────────────────────────────────────────────────
# Scadenze
# ───────────────────────────────────────────────────────────────────────────

OVERDUE_TASK_TITLE = "Test BCP scaduto — {title}"


def open_overdue_test_tasks() -> int:
    """Per ogni piano approvato con test scaduto o mai eseguito apre un task
    al Risk Manager, uno solo finché resta aperto. L'approvazione non cambia."""
    from apps.auth_grc.models import GrcRole
    from apps.tasks.models import Task
    from apps.tasks.services import create_task

    created = 0
    plans = BcpPlan.objects.filter(deleted_at__isnull=True, status="approvato").select_related("plant")
    open_ids = set(
        Task.objects.filter(
            source_module="M16", deleted_at__isnull=True, status__in=["aperto", "in_corso"],
        ).values_list("source_id", flat=True)
    )
    for plan in plans:
        today = _plant_today(plan.plant)
        if plan_test_state(plan.last_test_date, plan.next_test_date, today) == TEST_OK:
            continue
        if plan.pk in open_ids:
            continue
        create_task(
            plant=plan.plant,
            title=OVERDUE_TASK_TITLE.format(title=plan.title)[:300],
            description=(
                "Il piano BCP è approvato ma il test non è in regola (scaduto o mai "
                "eseguito): finché non viene registrato un test, i processi coperti "
                "risultano scoperti per test scaduto."
            ),
            priority="alta",
            source_module="M16",
            source_id=plan.pk,
            due_date=today + datetime.timedelta(days=30),
            assign_type="role",
            assign_value=GrcRole.RISK_MANAGER,
        )
        created += 1
    return created
