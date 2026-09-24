"""Rilevamento fornitori duplicati: P.IVA bloccante, ragione sociale solo avviso."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.suppliers.normalization import normalize_name, normalize_vat

User = get_user_model()

URL = "/api/v1/suppliers/suppliers/"
URL_CHECK = f"{URL}check-duplicates/"


# ── Normalizzazione ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,country,expected", [
    ("01234567890", "IT", "01234567890"),
    ("IT01234567890", "IT", "01234567890"),
    ("it 0123.4567-890", "IT", "01234567890"),
    (" 0123 4567 890 ", "IT", "01234567890"),
    ("RSSMRA80A01H501U", "IT", "RSSMRA80A01H501U"),   # codice fiscale: intatto
    ("DE123456789", "DE", "123456789"),
    ("EL123456789", "GR", "123456789"),                # prefisso IVA greco ≠ ISO
    ("DE123456789", "IT", "DE123456789"),              # prefisso di altro paese: resta
    ("", "IT", ""),
    (None, "IT", ""),
])
def test_normalize_vat(raw, country, expected):
    assert normalize_vat(raw, country) == expected


@pytest.mark.parametrize("raw,expected", [
    ("ROSSI S.r.l.", "rossi"),
    ("Rossi srl", "rossi"),
    ("Rossi  SRL.", "rossi"),
    ("Rossi & C. S.n.c.", "rossi"),
    ("&PLUS s.r.l. s.t.p.", "plus"),
    ("RESO' SRL", "reso"),
    ("Società Àlfa S.p.A.", "societa alfa"),
    ("Firma Sp. z o.o.", "firma"),
    ("Acme GmbH", "acme"),
    ("S.r.l.", "srl"),   # solo forma societaria: non si svuota
    ("", ""),
])
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


# ── Fixture ─────────────────────────────────────────────────────────────────

@pytest.fixture
def plants(db):
    from apps.plants.models import Plant
    a = Plant.objects.create(code="DUP-A", name="Plant A", country="IT", nis2_scope="non_soggetto", status="attivo")
    b = Plant.objects.create(code="DUP-B", name="Plant B", country="IT", nis2_scope="non_soggetto", status="attivo")
    return a, b


@pytest.fixture
def org_user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="dup_co", email="dup_co@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def client(org_user):
    c = APIClient()
    c.force_authenticate(user=org_user)
    return c


@pytest.fixture
def plant_b_client(db, plants):
    """Plant manager del solo Plant B."""
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="dup_pm", email="dup_pm@test.com", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    acc.scope_plants.set([plants[1]])
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def rossi(db, plants, org_user):
    """Fornitore esistente associato al solo Plant A."""
    from apps.suppliers.models import Supplier
    s = Supplier.objects.create(
        name="Rossi Meccanica S.r.l.", vat_number="01234567890", country="IT",
        email="info@rossi.example", created_by=org_user,
    )
    s.plants.add(plants[0])
    return s


def _payload(**kw):
    data = {"name": "Nuovo Fornitore", "vat_number": "09876543210", "country": "IT",
            "email": "nuovo@example.com"}
    data.update(kw)
    return data


# ── Model / vincolo DB ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_vat_normalized_computed_on_save(rossi):
    assert rossi.vat_normalized == "01234567890"
    rossi.vat_number = "IT 012 345 678 91"
    rossi.save(update_fields=["vat_number"])
    rossi.refresh_from_db()
    assert rossi.vat_normalized == "01234567891"


@pytest.mark.django_db
def test_db_constraint_blocks_same_vat(rossi):
    from apps.suppliers.models import Supplier
    with pytest.raises(IntegrityError), transaction.atomic():
        Supplier.objects.create(name="Altro", vat_number="IT01234567890", country="IT")


@pytest.mark.django_db
def test_db_constraint_ignores_deleted_and_blank(rossi):
    from apps.suppliers.models import Supplier
    rossi.soft_delete()
    Supplier.objects.create(name="Rossi di nuovo", vat_number="01234567890", country="IT")
    Supplier.objects.create(name="Senza PIVA 1", vat_number="")
    Supplier.objects.create(name="Senza PIVA 2", vat_number="")


# ── API: blocco P.IVA ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_with_same_vat_different_format_is_rejected(client, rossi):
    resp = client.post(URL, _payload(vat_number="IT 0123.4567.890"), format="json")
    assert resp.status_code == 400
    assert "Rossi Meccanica S.r.l." in resp.json()["vat_number"][0]


@pytest.mark.django_db
def test_create_same_vat_out_of_scope_hides_details(plant_b_client, plants, rossi):
    resp = plant_b_client.post(URL, _payload(vat_number="01234567890", plants=[str(plants[1].id)]), format="json")
    assert resp.status_code == 400
    msg = resp.json()["vat_number"][0]
    assert "Rossi" not in msg
    assert "perimetro" in msg


@pytest.mark.django_db
def test_create_after_soft_delete_is_allowed(client, rossi):
    rossi.soft_delete()
    resp = client.post(URL, _payload(vat_number="01234567890"), format="json")
    assert resp.status_code == 201


@pytest.mark.django_db
def test_patch_vat_onto_existing_supplier_is_rejected(client, rossi, org_user):
    from apps.suppliers.models import Supplier
    other = Supplier.objects.create(name="Bianchi", vat_number="11111111111", created_by=org_user)
    resp = client.patch(f"{URL}{other.id}/", {"vat_number": "IT01234567890"}, format="json")
    assert resp.status_code == 400
    assert "vat_number" in resp.json()


@pytest.mark.django_db
def test_patch_own_vat_reformatted_is_allowed(client, rossi):
    resp = client.patch(f"{URL}{rossi.id}/", {"vat_number": "IT 01234567890", "notes": "x"}, format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_with_similar_name_is_allowed_and_audited(client, rossi):
    from core.audit import AuditLog
    resp = client.post(URL, _payload(name="ROSSI MECCANICA SRL"), format="json")
    assert resp.status_code == 201
    log = AuditLog.objects.filter(action_code="suppliers.supplier.create").latest("timestamp_utc")
    assert log.payload["similar_names_count"] == 1


@pytest.mark.django_db
def test_vat_normalized_is_read_only(client, rossi):
    resp = client.patch(f"{URL}{rossi.id}/", {"vat_normalized": "X"}, format="json")
    assert resp.status_code == 200
    rossi.refresh_from_db()
    assert rossi.vat_normalized == "01234567890"


# ── API: check-duplicates ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_check_duplicates_vat_and_name(client, rossi):
    resp = client.post(URL_CHECK, {"name": "Rossi Meccanica", "vat_number": "IT01234567890", "country": "IT"}, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vat_match"]["visible"] is True
    assert body["vat_match"]["id"] == str(rossi.id)
    # il fornitore già segnalato per P.IVA non si ripete tra i nomi simili
    assert body["name_matches"] == []


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Rossi Meccanica", "ROSSI MECCANICA SPA", "Rossi Mecanica", "Rossi Meccanica Nord"])
def test_check_duplicates_similar_names(client, rossi, name):
    body = client.post(URL_CHECK, {"name": name, "vat_number": "", "country": "IT"}, format="json").json()
    assert body["vat_match"] is None
    assert [m["id"] for m in body["name_matches"]] == [str(rossi.id)]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Verdi Logistica", "Ro", "Meccanica"])
def test_check_duplicates_no_false_positive(client, rossi, name):
    body = client.post(URL_CHECK, {"name": name, "vat_number": "", "country": "IT"}, format="json").json()
    assert body["name_matches"] == []
    assert body["hidden_name_matches"] == 0


@pytest.mark.django_db
def test_check_duplicates_excludes_self(client, rossi):
    body = client.post(URL_CHECK, {
        "name": rossi.name, "vat_number": rossi.vat_number, "country": "IT", "exclude_id": str(rossi.id),
    }, format="json").json()
    assert body == {"vat_match": None, "name_matches": [], "hidden_name_matches": 0}


@pytest.mark.django_db
def test_check_duplicates_invalid_exclude_id(client):
    resp = client.post(URL_CHECK, {"name": "x", "exclude_id": "not-a-uuid"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_check_duplicates_out_of_scope_hides_details(plant_b_client, rossi):
    body = plant_b_client.post(URL_CHECK, {"name": "Rossi Meccanica", "vat_number": "01234567890", "country": "IT"}, format="json").json()
    assert body["vat_match"] == {"visible": False}
    assert body["name_matches"] == []

    body = plant_b_client.post(URL_CHECK, {"name": "Rossi Meccanica", "vat_number": "", "country": "IT"}, format="json").json()
    assert body["name_matches"] == []
    assert body["hidden_name_matches"] == 1


@pytest.mark.django_db
def test_check_duplicates_org_level_supplier_visible_to_plant_user(plant_b_client, org_user):
    """Fornitore senza siti = organizzativo → visibile a tutti."""
    from apps.suppliers.models import Supplier
    s = Supplier.objects.create(name="Fornitore Comune", vat_number="22222222222", created_by=org_user)
    body = plant_b_client.post(URL_CHECK, {"name": "", "vat_number": "22222222222", "country": "IT"}, format="json").json()
    assert body["vat_match"]["id"] == str(s.id)


@pytest.mark.django_db
def test_check_duplicates_forbidden_for_auditor(db, rossi):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="dup_aud", email="dup_aud@test.com", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    resp = c.post(URL_CHECK, {"name": "Rossi", "vat_number": "01234567890"}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_race_between_check_and_save_returns_400(client, rossi, monkeypatch):
    """Se due inserimenti superano insieme il controllo, il vincolo DB decide
    e la seconda richiesta riceve un 400, non un 500."""
    monkeypatch.setattr("apps.suppliers.services.find_vat_conflict", lambda *a, **kw: None)
    resp = client.post(URL, _payload(vat_number="01234567890"), format="json")
    assert resp.status_code == 400
    assert "vat_number" in resp.json()
