"""Regression test atomicità (P1-2): close_incident è multi-write (task NIS2 +
save incidente + PDCA + Lesson Learned + audit). Un fallimento a metà non deve
lasciare task orfani, lezioni spurie o l'incidente in stato incoerente."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="inc_atom", email="incatom@test.com", password="test")


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="INC-ATOM", name="Plant Inc Atom", country="IT",
        nis2_scope="essenziale", status="attivo",
    )


@pytest.fixture
def incident(db, plant, user):
    from apps.incidents.models import Incident
    return Incident.objects.create(
        plant=plant,
        title="Incidente Atomicità",
        description="Test atomicità",
        detected_at=timezone.now(),
        severity="alta",
        nis2_notifiable="no",
        is_significant=True,
        created_by=user,
    )


@pytest.mark.django_db
def test_close_incident_rolls_back_on_feed_failure(incident, user):
    """Se la creazione del PDCA post-incidente fallisce, l'incidente non deve
    risultare chiuso, e non devono restare task NIS2 o Lesson Learned orfani."""
    from apps.incidents.models import RCA
    from apps.incidents.services import close_incident
    from apps.lessons.models import LessonLearned
    from apps.tasks.models import Task

    RCA.objects.create(
        incident=incident,
        summary="Root cause",
        approved_at=timezone.now(),
        approved_by=user,
        created_by=user,
    )

    with mock.patch("apps.pdca.services.create_cycle", side_effect=RuntimeError("pdca down")):
        with pytest.raises(RuntimeError):
            close_incident(incident, user)

    incident.refresh_from_db()
    assert incident.status != "chiuso", "l'incidente non deve essere chiuso dopo il rollback"
    assert incident.closed_at is None
    assert not LessonLearned.objects.filter(source_module="M09", source_id=incident.pk).exists()
    assert not Task.objects.filter(source_module="M09", source_id=incident.pk).exists(), (
        "il task 'notifica formale mancante' deve essere annullato col rollback"
    )


@pytest.mark.django_db
def test_close_incident_fires_nis2_notification_on_success(incident, user):
    """Percorso felice con incidente NIS2 notificabile: chiusura ok + notifica
    NIS2 inviata (best-effort, fuori transazione)."""
    from apps.incidents.models import RCA
    from apps.incidents.services import close_incident

    incident.is_significant = False
    incident.nis2_notifiable = "si"
    incident.save(update_fields=["is_significant", "nis2_notifiable", "updated_at"])
    RCA.objects.create(
        incident=incident,
        summary="Root cause",
        approved_at=timezone.now(),
        approved_by=user,
        created_by=user,
    )

    with mock.patch("apps.notifications.resolver.fire_notification") as fire:
        result = close_incident(incident, user)

    assert result.status == "chiuso"
    fire.assert_called_once()


@pytest.mark.django_db
def test_close_incident_swallows_notification_error(incident, user):
    """La notifica NIS2 è best-effort: se fire_notification solleva, la chiusura
    (già committata) non deve fallire."""
    from apps.incidents.models import RCA
    from apps.incidents.services import close_incident

    incident.is_significant = False
    incident.nis2_notifiable = "si"
    incident.save(update_fields=["is_significant", "nis2_notifiable", "updated_at"])
    RCA.objects.create(
        incident=incident, summary="rc", approved_at=timezone.now(),
        approved_by=user, created_by=user,
    )

    with mock.patch(
        "apps.notifications.resolver.fire_notification", side_effect=RuntimeError("smtp down")
    ):
        result = close_incident(incident, user)  # non deve propagare

    assert result.status == "chiuso"


@pytest.mark.django_db
def test_mark_notification_sent_is_atomic(incident, user):
    """mark_notification_sent: registrazione notifica + audit insieme (happy path),
    e rollback completo se l'audit fallisce."""
    from apps.incidents.models import NIS2Notification
    from apps.incidents.nis2_services import mark_notification_sent

    notif = mark_notification_sent(
        incident, "formal_notification", user, protocol_ref="PROT-1",
    )
    assert notif.pk is not None
    assert NIS2Notification.objects.filter(incident=incident).count() == 1

    with mock.patch("core.audit.log_action", side_effect=RuntimeError("audit down")):
        with pytest.raises(RuntimeError):
            mark_notification_sent(incident, "early_warning", user)

    assert not NIS2Notification.objects.filter(
        incident=incident, notification_type="early_warning"
    ).exists()


@pytest.mark.django_db
def test_update_pdca_with_nis2_evidence_is_best_effort(incident, user):
    """Scelta di design (NON atomica): l'evidenza del report finale resta collegata
    anche se l'avanzamento PDCA fallisce — non va racchiusa in una transazione che
    la annullerebbe insieme all'avanzamento."""
    from apps.documents.models import Evidence
    from apps.incidents.models import NIS2Notification
    from apps.incidents.nis2_services import update_pdca_with_nis2_evidence
    from apps.pdca.models import PdcaCycle

    PdcaCycle.objects.create(
        plant=incident.plant,
        title="PDCA incidente",
        trigger_type="incidente",
        trigger_source_id=incident.pk,
        fase_corrente="do",
        created_by=user,
    )
    notif = NIS2Notification.objects.create(
        incident=incident,
        notification_type="final_report",
        csirt_name="CSIRT IT",
        sent_at=timezone.now(),
        sent_by=user,
        protocol_ref="PROT-FINAL",
        created_by=user,
    )

    # advance_phase fallisce → ma l'evidenza deve restare creata (best-effort).
    with mock.patch("apps.pdca.services.advance_phase", side_effect=RuntimeError("pdca err")):
        update_pdca_with_nis2_evidence(incident, notif)

    assert Evidence.objects.filter(title__startswith="Report Finale NIS2").exists()


@pytest.mark.django_db
def test_update_pdca_with_nis2_evidence_guards(incident, user):
    """Guardie: niente evidenza se non è un report finale o se manca il PDCA collegato."""
    from apps.documents.models import Evidence
    from apps.incidents.models import NIS2Notification
    from apps.incidents.nis2_services import update_pdca_with_nis2_evidence

    # 1) tipo diverso da final_report → ritorno immediato
    ew = NIS2Notification.objects.create(
        incident=incident, notification_type="early_warning",
        sent_at=timezone.now(), sent_by=user, created_by=user,
    )
    update_pdca_with_nis2_evidence(incident, ew)

    # 2) final_report ma nessun PDCA collegato → nessuna evidenza
    fr = NIS2Notification.objects.create(
        incident=incident, notification_type="final_report",
        sent_at=timezone.now(), sent_by=user, created_by=user,
    )
    update_pdca_with_nis2_evidence(incident, fr)

    assert not Evidence.objects.filter(title__startswith="Report Finale NIS2").exists()
