"""Riesame mirato (fase 1): tipo, ordine del giorno libero, documenti in attesa
selezionabili con revisione fissata, esiti e chiusura; respingimento per
delibera in M07."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/management-review/reviews/"
ITEMS = "/api/v1/management-review/agenda-items/"


@pytest.fixture
def plant(db):
    return _plant("TR-1")


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=f"Sito {code}", country="IT",
                                nis2_scope="essenziale", status="attivo")


@pytest.fixture
def co(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="tr_co", email="co@tr.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


def _api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _doc(plant, user, title, *, status="revisione", mandatory=True, code="", version="Rev. 01"):
    from apps.documents.models import Document
    from apps.documents.services import add_version

    doc = Document.objects.create(
        title=title, category="politica", document_type="policy", status=status, plant=plant,
        is_mandatory=mandatory, document_code=code, created_by=user,
    )
    if version:
        add_version(doc, "f.pdf", f"sha-{title}", f"p/{title}.pdf", user, "", 10, version_label=version)
        doc.refresh_from_db()
    return doc


def _targeted(co, plant, **kw):
    r = _api(co).post(URL, {"title": "Seduta CdA", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk), "kind": "mirato", **kw}, format="json")
    assert r.status_code == 201, r.data
    return r.data


# ── Tipo e ordine del giorno ─────────────────────────────────────────────────

def test_targeted_review_has_free_agenda_and_fixed_kind(co, plant):
    data = _targeted(co, plant)
    assert data["kind"] == "mirato" and data["agenda_items"] == []

    r = _api(co).patch(f"{URL}{data['id']}/", {"kind": "completo"}, format="json")
    assert r.status_code == 400

    r = _api(co).post(ITEMS, {"review": data["id"], "title": "Budget sicurezza"}, format="json")
    assert r.status_code == 201 and r.data["order"] == 0


def test_full_review_keeps_iso_agenda(co, plant):
    r = _api(co).post(URL, {"title": "Riesame annuale", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk)}, format="json")
    assert r.data["kind"] == "completo" and len(r.data["agenda_items"]) > 0


def test_targeted_review_rejects_snapshot_summary_and_ai(co, plant):
    rid = _targeted(co, plant)["id"]
    assert _api(co).post(f"{URL}{rid}/generate-snapshot/").status_code == 400
    assert _api(co).post(f"{URL}{rid}/summary/", {"text": "x"}, format="json").status_code == 400
    assert _api(co).post(f"{URL}{rid}/summary-draft/", {"lang": "it"}, format="json").status_code == 400


# ── Documenti in attesa ──────────────────────────────────────────────────────

def test_pending_documents_scope_and_states(co, plant):
    from apps.documents.services import add_version, approve_document, reject_document

    in_review = _doc(plant, co, "Politica accessi", code="D-2")
    draft = _doc(plant, co, "Procedura backup", status="bozza", mandatory=False, code="D-1")
    _doc(_plant("TR-2"), co, "Altro sito")
    # in vigore senza modifiche: non in attesa
    stable = _doc(plant, co, "Manuale", status="bozza", mandatory=False)
    approve_document(stable, co, mode="delibera", resolution_ref="1", resolution_date=timezone.localdate())
    # in vigore con una nuova versione non approvata (non obbligatorio: resta in vigore)
    changed = _doc(plant, co, "Registro asset", status="bozza", mandatory=False)
    approve_document(changed, co, mode="delibera", resolution_ref="2", resolution_date=timezone.localdate())
    add_version(changed, "g.pdf", "sha-new", "p/new.pdf", co, "", 10, version_label="Rev. 02")
    # ultima revisione già respinta: esce finché non ne arriva una nuova
    refused = _doc(plant, co, "Politica respinta")
    reject_document(refused, co, mode="delibera", resolution_ref="3", resolution_date=timezone.localdate())

    rid = _targeted(co, plant)["id"]
    rows = _api(co).get(f"{URL}{rid}/pending-documents/").data
    by_title = {r["title"]: r for r in rows}
    assert set(by_title) == {"Politica accessi", "Procedura backup", "Registro asset"}
    assert rows[0]["title"] == "Politica accessi"  # obbligatori per primi
    assert by_title["Registro asset"]["new_version"] is True
    assert by_title["Registro asset"]["version"] == "Rev. 02"
    assert by_title["Procedura backup"]["version"] == "Rev. 01"
    assert all(not r["selected"] for r in rows)
    assert str(in_review.pk) == by_title["Politica accessi"]["id"] and draft.pk


def test_pending_documents_query_count_is_constant(co, plant):
    rid = _targeted(co, plant)["id"]
    api = _api(co)
    _doc(plant, co, "D1")

    def count():
        with CaptureQueriesContext(connection) as ctx:
            assert api.get(f"{URL}{rid}/pending-documents/").status_code == 200
        return len(ctx.captured_queries)

    base = count()
    for i in range(5):
        _doc(plant, co, f"Altro {i}")
    assert count() == base


def test_pending_documents_only_for_targeted(co, plant):
    r = _api(co).post(URL, {"title": "Annuale", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk)}, format="json")
    assert _api(co).get(f"{URL}{r.data['id']}/pending-documents/").status_code == 400


def test_org_review_sees_all_sites(co, plant):
    _doc(plant, co, "Sito A")
    _doc(_plant("TR-3"), co, "Sito B")
    r = _api(co).post(URL, {"title": "Seduta", "review_date": str(timezone.localdate()), "kind": "mirato"},
                      format="json")
    titles = {row["title"] for row in _api(co).get(f"{URL}{r.data['id']}/pending-documents/").data}
    assert {"Sito A", "Sito B"} <= titles


# ── Selezione e revisione fissata ────────────────────────────────────────────

def test_select_documents_pins_version_and_skips_invalid(co, plant):
    doc = _doc(plant, co, "Politica accessi", code="D-10")
    no_file = _doc(plant, co, "Senza file", version="")
    other_site = _doc(_plant("TR-4"), co, "Altrove")
    rid = _targeted(co, plant)["id"]

    r = _api(co).post(f"{URL}{rid}/document-items/",
                      {"document_ids": [str(doc.pk), str(no_file.pk), str(other_site.pk)]}, format="json")
    assert r.status_code == 200, r.data
    assert len(r.data["added"]) == 1 and len(r.data["skipped"]) == 2
    item = next(i for i in r.data["review"]["agenda_items"] if i["code"] == "document")
    assert item["title"] == "[D-10] Politica accessi"
    assert item["document_info"]["examined_version"] == "Rev. 01"
    assert item["document_info"]["version_changed"] is False

    again = _api(co).post(f"{URL}{rid}/document-items/", {"document_ids": [str(doc.pk)]}, format="json")
    assert again.data["added"] == [] and again.data["skipped"][0]["id"] == str(doc.pk)
    listed = _api(co).get(f"{URL}{rid}/pending-documents/").data
    assert next(r for r in listed if r["id"] == str(doc.pk))["selected"] is True


def test_document_items_not_on_full_review(co, plant):
    doc = _doc(plant, co, "Politica")
    r = _api(co).post(URL, {"title": "Annuale", "review_date": str(timezone.localdate()),
                            "plant": str(plant.pk)}, format="json")
    resp = _api(co).post(f"{URL}{r.data['id']}/document-items/", {"document_ids": [str(doc.pk)]}, format="json")
    assert resp.status_code == 400


def _selected_item(co, plant, doc):
    rid = _targeted(co, plant)["id"]
    r = _api(co).post(f"{URL}{rid}/document-items/", {"document_ids": [str(doc.pk)]}, format="json")
    item = next(i for i in r.data["review"]["agenda_items"] if i["code"] == "document")
    return rid, item["id"]


def test_outcome_rules(co, plant):
    from apps.documents.services import add_version

    doc = _doc(plant, co, "Politica accessi")
    rid, item_id = _selected_item(co, plant, doc)
    api = _api(co)

    assert api.patch(f"{ITEMS}{item_id}/", {"document_outcome": "boh"}, format="json").status_code == 400
    r = api.patch(f"{ITEMS}{item_id}/", {"document_outcome": "approvato", "discussion": "Ok"}, format="json")
    assert r.status_code == 200 and r.data["document_outcome"] == "approvato"

    custom = api.post(ITEMS, {"review": rid, "title": "Altro"}, format="json").data["id"]
    assert api.patch(f"{ITEMS}{custom}/", {"document_outcome": "approvato"}, format="json").status_code == 400

    # nuova revisione dopo la selezione: esito bloccato finché non si riallinea
    add_version(doc, "h.pdf", "sha-rev2", "p/rev2.pdf", co, "", 10, version_label="Rev. 02")
    item = api.get(f"{ITEMS}{item_id}/").data
    assert item["document_info"]["version_changed"] is True
    assert item["document_info"]["latest_version"] == "Rev. 02"
    assert api.patch(f"{ITEMS}{item_id}/", {"document_outcome": "respinto"}, format="json").status_code == 400

    r = api.post(f"{ITEMS}{item_id}/refresh-version/")
    assert r.status_code == 200, r.data
    assert r.data["document_outcome"] == "" and r.data["document_info"]["examined_version"] == "Rev. 02"
    assert api.post(f"{ITEMS}{item_id}/refresh-version/").status_code == 400


# ── Chiusura ─────────────────────────────────────────────────────────────────

def test_close_targeted_review(co, plant):
    from apps.management_review.models import ManagementReview

    empty = _targeted(co, plant)["id"]
    assert _api(co).post(f"{URL}{empty}/complete/").status_code == 400

    doc = _doc(plant, co, "Politica accessi")
    rid, item_id = _selected_item(co, plant, doc)
    r = _api(co).post(f"{URL}{rid}/complete/")
    assert r.status_code == 400 and r.data["code"] == "document_outcome_missing"

    _api(co).patch(f"{ITEMS}{item_id}/", {"document_outcome": "rinviato"}, format="json")
    r = _api(co).post(f"{URL}{rid}/complete/")
    assert r.status_code == 200 and r.data["status"] == "completato"
    assert ManagementReview.objects.get(pk=rid).next_review_date is None

    # a riunione chiusa l'ordine del giorno non cambia
    other = _doc(plant, co, "Altra")
    assert _api(co).post(f"{URL}{rid}/document-items/", {"document_ids": [str(other.pk)]},
                         format="json").status_code == 400


# ── M07: respingimento per delibera ──────────────────────────────────────────

def test_reject_by_resolution(co, plant):
    from apps.documents.models import DocumentApproval
    from apps.documents.services import reject_document

    today = timezone.localdate()
    in_review = _doc(plant, co, "In revisione")
    reject_document(in_review, co, "No", mode="delibera", resolution_ref="7", resolution_date=today)
    in_review.refresh_from_db()
    rec = DocumentApproval.objects.get(document=in_review, action="reject")
    assert in_review.status == "bozza"
    assert rec.approval_mode == "delibera" and rec.version.version_label == "Rev. 01"
    assert rec.resolution_ref == "7" and rec.resolution_date == today

    draft = _doc(plant, co, "Bozza", status="bozza")
    reject_document(draft, co, mode="delibera", resolution_ref="8", resolution_date=today)
    draft.refresh_from_db()
    assert draft.status == "bozza"

    # l'autore registra il respingimento dell'organo: nessuna separazione dei compiti
    assert DocumentApproval.objects.filter(document=draft, action="reject").exists()

    with pytest.raises(ValidationError):
        reject_document(draft, co, mode="delibera", resolution_ref="9", resolution_date=date(2999, 1, 1))


def test_resolution_on_new_version_of_document_in_force(co, plant):
    from apps.documents.models import DocumentApproval
    from apps.documents.services import add_version, approve_document, reject_document

    today = timezone.localdate()
    doc = _doc(plant, co, "Registro", status="bozza", mandatory=False)
    approve_document(doc, co, mode="delibera", resolution_ref="1", resolution_date=today)
    add_version(doc, "n.pdf", "sha-n", "p/n.pdf", co, "", 10, version_label="Rev. 02")
    doc.refresh_from_db()
    assert doc.status == "approvato"

    reject_document(doc, co, mode="delibera", resolution_ref="2", resolution_date=today)
    doc.refresh_from_db()
    assert doc.status == "approvato"  # resta in vigore la revisione già approvata
    assert DocumentApproval.objects.get(document=doc, action="reject").version.version_label == "Rev. 02"

    add_version(doc, "m.pdf", "sha-m", "p/m.pdf", co, "", 10, version_label="Rev. 03")
    approve_document(doc, co, mode="delibera", resolution_ref="3", resolution_date=today)
    latest = DocumentApproval.objects.filter(document=doc, action="approve").latest("created_at")
    assert latest.version.version_label == "Rev. 03"
