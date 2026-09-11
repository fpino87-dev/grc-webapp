"""Valutazione corrente del fornitore: data/scadenza/origine derivate.

La data di valutazione non si inserisce più a mano nell'anagrafica: arriva dal
questionario valutato, da una valutazione esistente registrata o da un audit
terze parti approvato (vedi `risk_adj._latest_evaluation`).
"""
import datetime
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.suppliers.models import (
    QuestionnaireTemplate,
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierQuestionnaire,
)
from apps.suppliers.services import (
    approve_assessment,
    register_evaluation,
    register_existing_evaluation,
)

User = get_user_model()

URL_SUPPLIERS = "/api/v1/suppliers/suppliers/"
URL_QUESTIONNAIRES = "/api/v1/suppliers/questionnaires/"


def _days(n):
    return datetime.timedelta(days=n)


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="evs_user", email="evs@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(code="EVS-P", name="Plant EVS", country="IT", nis2_scope="non_soggetto", status="attivo")


@pytest.fixture
def supplier(db, user, plant):
    s = Supplier.objects.create(
        name="Eval Co", vat_number="99887766554", email="eval@example.com",
        risk_level="basso", status="attivo", created_by=user,
    )
    s.plants.add(plant)
    return s


@pytest.fixture
def config(db):
    return SupplierEvaluationConfig.get_solo()


@pytest.fixture
def pending(db, supplier, user):
    template = QuestionnaireTemplate.objects.create(
        name="T", subject="S", body="B", form_url="https://example.com/f", created_by=user,
    )
    now = timezone.now()
    return SupplierQuestionnaire.objects.create(
        supplier=supplier, template=template, sent_at=now, last_sent_at=now,
        sent_to=supplier.email, sent_by=user, status="inviato", created_by=user,
    )


# ── Derivazione ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_questionnaire_evaluation_sets_date_expiry_and_source(supplier, pending, user, config):
    day = timezone.localdate() - _days(3)
    register_evaluation(pending, day, "alto", user)
    supplier.refresh_from_db()
    pending.refresh_from_db()
    assert supplier.evaluation_date == day
    assert supplier.evaluation_expires_at == pending.expires_at
    assert pending.expires_at == day + _days(config.questionnaire_validity_months * 30)
    assert supplier.evaluation_source == "questionario"
    assert supplier.risk_level == "alto"


@pytest.mark.django_db
def test_evaluation_rejects_future_date_and_invalid_risk(pending, user):
    with pytest.raises(ValidationError):
        register_evaluation(pending, timezone.localdate() + _days(1), "alto", user)
    with pytest.raises(ValidationError):
        register_evaluation(pending, timezone.localdate(), "altissimo", user)


@pytest.mark.django_db
def test_approved_audit_newer_than_questionnaire_becomes_current(supplier, pending, user, config):
    register_evaluation(pending, timezone.localdate() - _days(60), "medio", user)
    audit_day = timezone.localdate() - _days(5)
    assessment = SupplierAssessment.objects.create(
        supplier=supplier, assessment_date=audit_day, status="completato",
        score_overall=80, created_by=user,
    )
    approve_assessment(assessment, user, notes="ok")
    supplier.refresh_from_db()
    assert supplier.evaluation_date == audit_day
    assert supplier.evaluation_source == "audit"
    assert supplier.evaluation_expires_at == audit_day + _days(config.assessment_validity_months * 30)


@pytest.mark.django_db
def test_no_evaluation_leaves_fields_empty(supplier):
    from apps.suppliers.risk_adj import recompute_risk_adj
    recompute_risk_adj(supplier)
    supplier.refresh_from_db()
    assert supplier.evaluation_date is None
    assert supplier.evaluation_expires_at is None
    assert supplier.evaluation_source == ""


# ── Valutazione esistente ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_existing_evaluation_creates_record_without_email(supplier, user):
    day = timezone.localdate() - _days(100)
    with mock.patch("apps.notifications.services.send_grc_email") as send:
        q = register_existing_evaluation(supplier, day, "medio", user, notes="Questionario cartaceo 2026")
    send.assert_not_called()
    assert q.origin == "esistente"
    assert q.status == "risposto"
    assert q.send_count == 0
    assert q.template is None
    supplier.refresh_from_db()
    assert supplier.evaluation_date == day
    assert supplier.evaluation_source == "esistente"
    assert supplier.evaluation_expires_at == q.expires_at
    assert supplier.risk_level == "medio"


@pytest.mark.django_db
def test_register_existing_requires_notes_and_past_date(supplier, user):
    with pytest.raises(ValidationError):
        register_existing_evaluation(supplier, timezone.localdate(), "medio", user, notes="  ")
    with pytest.raises(ValidationError):
        register_existing_evaluation(supplier, timezone.localdate() + _days(2), "medio", user, notes="rif")
    assert not SupplierQuestionnaire.objects.filter(supplier=supplier).exists()


@pytest.mark.django_db
def test_older_existing_evaluation_does_not_override_newer(supplier, pending, user):
    recent = timezone.localdate() - _days(10)
    register_evaluation(pending, recent, "alto", user)
    register_existing_evaluation(supplier, recent - _days(400), "basso", user, notes="Storico")
    supplier.refresh_from_db()
    assert supplier.evaluation_date == recent
    assert supplier.evaluation_source == "questionario"
    assert supplier.risk_level == "alto"


# ── API ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_evaluation_fields_are_read_only_via_api(client, supplier):
    resp = client.patch(
        f"{URL_SUPPLIERS}{supplier.id}/",
        {"evaluation_date": "2026-01-01", "evaluation_expires_at": "2030-01-01", "evaluation_source": "audit"},
        format="json",
    )
    assert resp.status_code == 200
    supplier.refresh_from_db()
    assert supplier.evaluation_date is None
    assert supplier.evaluation_expires_at is None
    assert supplier.evaluation_source == ""


@pytest.mark.django_db
def test_api_register_existing(client, supplier):
    day = (timezone.localdate() - _days(30)).isoformat()
    payload = {"supplier_id": str(supplier.id), "evaluation_date": day, "risk_result": "alto", "notes": "Audit 2026 cartaceo"}
    resp = client.post(f"{URL_QUESTIONNAIRES}register-existing/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["origin"] == "esistente"

    detail = client.get(f"{URL_SUPPLIERS}{supplier.id}/").data
    assert detail["evaluation_date"] == day
    assert detail["evaluation_source"] == "esistente"
    assert detail["evaluation_expires_at"]
    # Una valutazione registrata non è un invio: il pulsante "Invia" resta libero.
    assert detail["latest_questionnaire_status"] is None

    bad = client.post(f"{URL_QUESTIONNAIRES}register-existing/", {**payload, "notes": ""}, format="json")
    assert bad.status_code == 400


@pytest.mark.django_db
def test_api_register_existing_respects_plant_scope(db, supplier):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.plants.models import Plant

    other = Plant.objects.create(code="EVS-O", name="Other", country="IT", nis2_scope="non_soggetto", status="attivo")
    pm = User.objects.create_user(username="evs_pm", email="evspm@test.com", password="x")
    access = UserPlantAccess.objects.create(user=pm, role=GrcRole.COMPLIANCE_OFFICER, scope_type="single_plant")
    access.scope_plants.set([other])
    c = APIClient()
    c.force_authenticate(user=pm)
    resp = c.post(
        f"{URL_QUESTIONNAIRES}register-existing/",
        {"supplier_id": str(supplier.id), "evaluation_date": timezone.localdate().isoformat(),
         "risk_result": "medio", "notes": "x"},
        format="json",
    )
    assert resp.status_code == 403
    assert not SupplierQuestionnaire.objects.filter(supplier=supplier).exists()


@pytest.mark.django_db
def test_api_delete_questionnaire_is_soft_and_recomputes(client, supplier, user):
    q = register_existing_evaluation(supplier, timezone.localdate() - _days(5), "medio", user, notes="rif")
    resp = client.delete(f"{URL_QUESTIONNAIRES}{q.id}/")
    assert resp.status_code == 204
    assert SupplierQuestionnaire.objects.all_with_deleted().filter(pk=q.pk, deleted_at__isnull=False).exists()
    supplier.refresh_from_db()
    assert supplier.evaluation_date is None
    assert supplier.evaluation_source == ""


@pytest.mark.django_db
def test_api_filter_unevaluated(client, supplier, user):
    evaluated = Supplier.objects.create(name="Valutato", vat_number="1", status="attivo", created_by=user)
    register_existing_evaluation(evaluated, timezone.localdate(), "alto", user, notes="rif")
    names = {s["name"] for s in client.get(URL_SUPPLIERS, {"risk_adj_missing": "true"}).data["results"]}
    assert "Eval Co" in names
    assert "Valutato" not in names
    names = {s["name"] for s in client.get(URL_SUPPLIERS, {"risk_adj": "alto"}).data["results"]}
    assert names == {"Valutato"}


@pytest.mark.django_db
def test_csv_export_includes_evaluation_expiry(client, supplier, user):
    q = register_existing_evaluation(supplier, timezone.localdate() - _days(5), "medio", user, notes="rif")
    resp = client.get(f"{URL_SUPPLIERS}export-csv/")
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    assert "Scadenza valutazione" in content.splitlines()[0]
    assert str(q.expires_at) in content


# ── Migrazione date manuali ────────────────────────────────────────────────

@pytest.mark.django_db
def test_migration_converts_unbacked_manual_dates(user):
    import importlib
    from django.apps import apps as django_apps

    migration = importlib.import_module("apps.suppliers.migrations.0016_supplier_evaluation_derived")
    past = timezone.localdate() - _days(200)
    future = timezone.localdate() + _days(90)
    legacy = Supplier.objects.create(
        name="Legacy", vat_number="L", status="attivo", risk_level="alto",
        evaluation_date=past, created_by=user,
    )
    contract = Supplier.objects.create(
        name="Contratto", vat_number="C", status="attivo", notes="Nota esistente",
        evaluation_date=future, created_by=user,
    )

    migration.forwards(django_apps, None)

    legacy.refresh_from_db()
    q = SupplierQuestionnaire.objects.get(supplier=legacy)
    assert q.origin == "esistente" and q.risk_result == "alto" and q.evaluation_date == past
    assert legacy.evaluation_date == past
    assert legacy.evaluation_source == "esistente"
    assert legacy.evaluation_expires_at == q.expires_at

    contract.refresh_from_db()
    assert not SupplierQuestionnaire.objects.filter(supplier=contract).exists()
    assert contract.evaluation_date is None
    assert contract.notes.startswith("Nota esistente\n[Migrazione]")
    assert future.isoformat() in contract.notes
