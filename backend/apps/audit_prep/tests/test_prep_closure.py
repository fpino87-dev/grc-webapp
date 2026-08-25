"""
Chiusura di un audit prep: promemoria e programma annuale.

Concludere un prep — completandolo o annullandolo — deve chiudere i suoi
promemoria e riallineare il programma annuale. Le azioni dedicate non passano
da `perform_update`, quindi non ereditavano nessuna delle due cose.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/audit-prep/audit-preps/"


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="cl_u", email="cl@test.com", password="x")
    UserPlantAccess.objects.create(
        user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org"
    )
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="CL-P", name="Plant Closure", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def program(db, plant, user):
    """Programma annuale con un audit pianificato e in corso."""
    from apps.audit_prep.models import AuditProgram
    return AuditProgram.objects.create(
        plant=plant, year=2026, status="in_corso", created_by=user,
        planned_audits=[{
            "id": "a1", "quarter": 2, "title": "Audit Q2",
            "planned_date": "2026-06-01", "status": "in_progress",
            "framework_codes": ["ISO27001"],
        }],
    )


@pytest.fixture
def prep(db, plant, program, user):
    from apps.audit_prep.models import AuditPrep
    p = AuditPrep.objects.create(
        plant=plant, title="Audit Q2 2026", audit_date=timezone.localdate(),
        status="in_corso", audit_program=program, created_by=user,
    )
    program.planned_audits[0]["audit_prep_id"] = str(p.pk)
    program.save(update_fields=["planned_audits"])
    return p


def _reminder(plant, prep, user, title="Audit prep bloccato: Audit Q2 2026"):
    from apps.tasks.services import create_task
    return create_task(
        plant=plant, title=title, description="Promemoria",
        priority="alta", source_module="M17", source_id=prep.pk,
        due_date=timezone.localdate(),
        assign_type="role", assign_value="compliance_officer",
    )


# ── Completamento ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_completing_closes_the_reminders(client, plant, prep, user):
    from apps.tasks.models import Task

    t1 = _reminder(plant, prep, user)
    t2 = _reminder(plant, prep, user)

    resp = client.post(f"{URL}{prep.id}/complete/")
    assert resp.status_code == 200, resp.data
    assert resp.data["reminders_closed"] == 2

    for t in (t1, t2):
        t.refresh_from_db()
        assert t.status == "completato"
        assert "completato" in t.notes.lower()
    assert not Task.objects.filter(
        source_id=prep.pk, status__in=["aperto", "in_corso"]
    ).exists()


@pytest.mark.django_db
def test_completing_marks_the_audit_completed_in_the_program(client, prep, program):
    """Il caso segnalato: prep completato ma nel programma annuale l'audit
    restava «in corso»."""
    resp = client.post(f"{URL}{prep.id}/complete/")
    assert resp.status_code == 200, resp.data

    program.refresh_from_db()
    assert program.planned_audits[0]["status"] == "completed"
    assert program.status == "completato"


@pytest.mark.django_db
def test_reminders_of_other_preps_are_untouched(client, plant, prep, program, user):
    from apps.audit_prep.models import AuditPrep
    from apps.tasks.models import Task

    other = AuditPrep.objects.create(
        plant=plant, title="Audit Q3 2026", audit_date=timezone.localdate(),
        status="in_corso", created_by=user,
    )
    foreign = _reminder(plant, other, user, title="Audit prep bloccato: Audit Q3 2026")

    client.post(f"{URL}{prep.id}/complete/")

    foreign.refresh_from_db()
    assert foreign.status == "aperto"
    assert Task.objects.filter(source_id=other.pk, status="aperto").exists()


# ── Annullamento ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cancelling_closes_reminders_and_updates_the_program(client, plant, prep, program, user):
    reminder = _reminder(plant, prep, user)

    resp = client.post(
        f"{URL}{prep.id}/annulla/",
        {"reason": "Aperto per errore sul sito sbagliato"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["reminders_closed"] == 1

    reminder.refresh_from_db()
    assert reminder.status == "completato"
    assert "annullato" in reminder.notes.lower()

    program.refresh_from_db()
    assert program.planned_audits[0]["status"] == "cancelled"


# ── Deduplica del giro settimanale ───────────────────────────────────────────

@pytest.mark.django_db
def test_the_weekly_job_does_not_pile_up_reminders(plant, prep, user):
    """Il difetto: creare il promemoria non tocca il prep, che resta «fermo»,
    e il lunedì dopo ne nasceva un altro identico. Undici settimane, undici
    task."""
    from apps.audit_prep.models import AuditPrep
    from apps.audit_prep.tasks import check_stale_audit_preps
    from apps.tasks.models import Task

    AuditPrep.objects.filter(pk=prep.pk).update(
        updated_at=timezone.now() - timezone.timedelta(days=45)
    )

    for _ in range(3):
        check_stale_audit_preps()

    assert Task.objects.filter(
        source_id=prep.pk, title__startswith="Audit prep bloccato"
    ).count() == 1


@pytest.mark.django_db
def test_a_completed_prep_gets_no_new_reminder(plant, prep, user):
    from apps.audit_prep.models import AuditPrep
    from apps.audit_prep.tasks import check_stale_audit_preps
    from apps.tasks.models import Task

    AuditPrep.objects.filter(pk=prep.pk).update(
        status="completato",
        updated_at=timezone.now() - timezone.timedelta(days=45),
    )
    check_stale_audit_preps()

    assert not Task.objects.filter(source_id=prep.pk).exists()


# ── Promemoria agganciati al programma ───────────────────────────────────────

def _program_reminder(plant, program, user, quarter=2):
    """I promemoria del programma annuale nascono prima del prep, quindi sono
    agganciati al programma: `source_id` è il programma, non il prep."""
    from apps.tasks.services import create_task
    return create_task(
        plant=plant,
        title=f"Preparazione audit Q{quarter}: Audit Q{quarter} 2026",
        description="Promemoria di preparazione",
        priority="media", source_module="M17", source_id=program.pk,
        due_date=timezone.localdate(),
        assign_type="role", assign_value="compliance_officer",
    )


@pytest.mark.django_db
def test_completing_closes_the_programme_reminder_too(client, plant, prep, program, user):
    """«Preparazione audit Q2» è agganciato al programma: senza questo passo
    sopravviveva alla chiusura dell'audit che lo aveva motivato."""
    reminder = _program_reminder(plant, program, user, quarter=2)

    resp = client.post(f"{URL}{prep.id}/complete/")
    assert resp.status_code == 200, resp.data

    reminder.refresh_from_db()
    assert reminder.status == "completato"


@pytest.mark.django_db
def test_reminders_of_other_quarters_survive(client, plant, prep, program, user):
    """Chiudere l'audit del secondo trimestre non deve toccare il terzo."""
    q2 = _program_reminder(plant, program, user, quarter=2)
    q3 = _program_reminder(plant, program, user, quarter=3)

    client.post(f"{URL}{prep.id}/complete/")

    q2.refresh_from_db()
    q3.refresh_from_db()
    assert q2.status == "completato"
    assert q3.status == "aperto", "il Q3 non è stato ancora fatto"


@pytest.mark.django_db
def test_a_prep_outside_any_programme_closes_only_its_own(client, plant, user):
    from apps.audit_prep.models import AuditPrep
    from apps.tasks.models import Task

    standalone = AuditPrep.objects.create(
        plant=plant, title="Audit spot", audit_date=timezone.localdate(),
        status="in_corso", created_by=user,
    )
    own = _reminder(plant, standalone, user, title="Audit prep bloccato: Audit spot")

    resp = client.post(f"{URL}{standalone.id}/complete/")
    assert resp.status_code == 200, resp.data
    assert resp.data["reminders_closed"] == 1

    own.refresh_from_db()
    assert own.status == "completato"
    assert not Task.objects.filter(status="aperto", source_module="M17").exists()
