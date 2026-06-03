"""Regression: check_questionnaire_followups deve inviare UN SOLO riepilogo per
operatore (non una mail per questionario, che girando periodicamente faceva spam)."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def operator(db):
    return User.objects.create_user(username="op", email="op@azienda.it", password="x")


def make_questionnaire(supplier_name, operator, send_count, days_ago, user, sent_to="f@vend.it"):
    from apps.suppliers.models import Supplier, SupplierQuestionnaire
    supplier = Supplier.objects.create(name=supplier_name, status="attivo", created_by=user)
    sent = timezone.now() - timezone.timedelta(days=days_ago)
    return SupplierQuestionnaire.objects.create(
        supplier=supplier,
        sent_at=sent,
        last_sent_at=sent,
        sent_to=sent_to,
        sent_by=operator,
        send_count=send_count,
        status="inviato",
        created_by=user,
    )


@pytest.mark.django_db
def test_single_digest_email_per_operator(operator):
    from apps.suppliers.services import check_questionnaire_followups

    # 3 questionari dello stesso operatore, tutti oltre la soglia di 7 giorni
    make_questionnaire("ACME", operator, send_count=4, days_ago=21, user=operator)   # 3-strike
    make_questionnaire("Beta", operator, send_count=1, days_ago=10, user=operator)   # follow-up
    make_questionnaire("Gamma", operator, send_count=2, days_ago=9, user=operator)   # follow-up

    with mock.patch("apps.notifications.services.send_grc_email") as send:
        check_questionnaire_followups()

    # UNA sola mail (non 3)
    assert send.call_count == 1
    kwargs = send.call_args.kwargs
    assert kwargs["recipients"] == ["op@azienda.it"]
    assert "3 fornitori" in kwargs["subject"]
    body = kwargs["body"]
    # contiene tutti e tre i fornitori, con le due sezioni
    assert "ACME" in body and "Beta" in body and "Gamma" in body
    assert "3+ tentativi" in body
    assert "Follow-up" in body


@pytest.mark.django_db
def test_one_email_per_distinct_operator(operator, db):
    from apps.suppliers.services import check_questionnaire_followups

    other = User.objects.create_user(username="op2", email="op2@azienda.it", password="x")
    make_questionnaire("ACME", operator, send_count=1, days_ago=10, user=operator)
    make_questionnaire("Beta", operator, send_count=1, days_ago=10, user=operator)
    make_questionnaire("Gamma", other, send_count=1, days_ago=10, user=other)

    with mock.patch("apps.notifications.services.send_grc_email") as send:
        check_questionnaire_followups()

    # un riepilogo per ciascuno dei due operatori
    assert send.call_count == 2
    recipients = sorted(c.kwargs["recipients"][0] for c in send.call_args_list)
    assert recipients == ["op2@azienda.it", "op@azienda.it"]


@pytest.mark.django_db
def test_skips_recent_and_responded(operator):
    from apps.suppliers.services import check_questionnaire_followups
    from apps.suppliers.models import SupplierQuestionnaire

    # entro i 7 giorni → escluso
    make_questionnaire("Recent", operator, send_count=1, days_ago=2, user=operator)
    # già valutato → escluso
    q = make_questionnaire("Done", operator, send_count=1, days_ago=30, user=operator)
    q.evaluation_date = timezone.now().date()
    q.save(update_fields=["evaluation_date"])

    with mock.patch("apps.notifications.services.send_grc_email") as send:
        check_questionnaire_followups()

    assert send.call_count == 0


@pytest.mark.django_db
def test_skips_operator_without_email(db):
    from apps.suppliers.services import check_questionnaire_followups

    no_email = User.objects.create_user(username="noemail", email="", password="x")
    make_questionnaire("Orphan", no_email, send_count=1, days_ago=10, user=no_email)

    with mock.patch("apps.notifications.services.send_grc_email") as send:
        check_questionnaire_followups()

    assert send.call_count == 0
