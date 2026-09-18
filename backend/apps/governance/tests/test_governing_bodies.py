"""Organi di governo (CdA, comitato, direzione) e componenti: validazioni,
perimetro per sito, dati personali visibili solo a chi vede il sito."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/governance/committees/"
URL_MEMBERS = "/api/v1/governance/committee-members/"


@pytest.fixture
def plants(db):
    from apps.plants.models import Plant
    return [
        Plant.objects.create(code=c, name=f"Sito {c}", country="IT",
                             nis2_scope="non_soggetto", status="attivo")
        for c in ("GB-A", "GB-B")
    ]


def _client(role, scope="org", plants=()):
    from apps.auth_grc.models import UserPlantAccess
    u = User.objects.create_user(username=f"gb_{role}_{scope}", email=f"{role}{scope}@gb.test", password="x")
    acc = UserPlantAccess.objects.create(user=u, role=role, scope_type=scope)
    for p in plants:
        acc.scope_plants.add(p)
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.fixture
def co():
    from apps.auth_grc.models import GrcRole
    return _client(GrcRole.COMPLIANCE_OFFICER)


def _member(committee, name, role="membro", **kw):
    from apps.governance.models import CommitteeMember
    return CommitteeMember.objects.create(
        committee=committee, full_name=name, body_role=role,
        valid_from=kw.pop("valid_from", date(2025, 1, 1)), **kw,
    )


@pytest.mark.django_db
def test_create_body_and_members_without_account(co):
    client, _ = co
    resp = client.post(URL, {"name": "CdA", "committee_type": "cda"}, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["is_management_body"] is True
    body = resp.data["id"]
    resp = client.post(URL_MEMBERS, {
        "committee": body, "full_name": "Paola Neri", "position": "Presidente CdA",
        "body_role": "presidente", "valid_from": "2025-01-01",
    }, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["user"] is None and resp.data["is_active"] is True
    members = client.get(f"{URL}{body}/").data["members"]
    assert [m["full_name"] for m in members] == ["Paola Neri"]


@pytest.mark.django_db
def test_single_president_at_a_time(co):
    from apps.governance.models import SecurityCommittee
    client, _ = co
    body = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    _member(body, "Primo", "presidente", valid_until=date(2025, 12, 31))
    base = {"committee": str(body.id), "full_name": "Secondo", "body_role": "presidente"}
    # periodo sovrapposto → rifiutato
    assert client.post(URL_MEMBERS, {**base, "valid_from": "2025-06-01"}, format="json").status_code == 400
    # dopo la fine della carica precedente → ammesso
    assert client.post(URL_MEMBERS, {**base, "valid_from": "2026-01-01"}, format="json").status_code == 201


@pytest.mark.django_db
def test_member_period_and_account_validation(co):
    from apps.governance.models import SecurityCommittee
    client, u = co
    body = SecurityCommittee.objects.create(name="Comitato", committee_type="comitato")
    resp = client.post(URL_MEMBERS, {"committee": str(body.id), "full_name": "X",
                                     "valid_from": "2025-06-01", "valid_until": "2025-01-01"}, format="json")
    assert resp.status_code == 400 and "valid_until" in resp.data
    _member(body, "Con account", user=u)
    resp = client.post(URL_MEMBERS, {"committee": str(body.id), "full_name": "Doppione",
                                     "user": u.id, "valid_from": "2025-03-01"}, format="json")
    assert resp.status_code == 400 and "user" in resp.data


@pytest.mark.django_db
def test_visibility_by_plant_scope(plants):
    """Chi vede solo il sito A vede gli organi di organizzazione e quelli del
    sito A — non i componenti dell'organo del sito B."""
    from apps.auth_grc.models import GrcRole
    from apps.governance.models import SecurityCommittee
    org = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    a = SecurityCommittee.objects.create(name="Comitato A")
    a.plants.add(plants[0])
    b = SecurityCommittee.objects.create(name="Comitato B")
    b.plants.add(plants[1])
    _member(b, "Riservato B")

    client, _ = _client(GrcRole.PLANT_MANAGER, "single_plant", [plants[0]])
    names = {c["name"] for c in client.get(URL).data["results"]}
    assert names == {org.name, a.name}
    assert client.get(URL_MEMBERS).data["count"] == 0


@pytest.mark.django_db
def test_plant_scoped_governance_cannot_touch_org_body(plants):
    from apps.auth_grc.models import GrcRole
    from apps.governance.models import SecurityCommittee
    org = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    client, _ = _client(GrcRole.COMPLIANCE_OFFICER, "single_plant", [plants[0]])
    assert client.patch(f"{URL}{org.id}/", {"name": "Hack"}, format="json").status_code == 403
    assert client.post(URL, {"name": "Nuovo org", "committee_type": "comitato"}, format="json").status_code == 403
    resp = client.post(URL, {"name": "Comitato A", "plants": [str(plants[0].id)]}, format="json")
    assert resp.status_code == 201
    resp = client.post(URL, {"name": "Comitato B", "plants": [str(plants[1].id)]}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_member_in_a_review_cannot_be_deleted(co):
    from apps.governance.models import SecurityCommittee
    from apps.management_review.models import ManagementReview, ReviewParticipant
    client, _ = co
    body = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    m = _member(body, "Paola Neri", "presidente")
    review = ManagementReview.objects.create(title="R", review_date=date(2026, 3, 1), governing_body=body)
    ReviewParticipant.objects.create(review=review, member=m, full_name=m.full_name)
    resp = client.delete(f"{URL_MEMBERS}{m.id}/")
    assert resp.status_code == 400
    # la carica si chiude con la data di fine
    assert client.patch(f"{URL_MEMBERS}{m.id}/", {"valid_until": "2026-06-30"}, format="json").status_code == 200


@pytest.mark.django_db
def test_audit_payload_has_no_names(co):
    from apps.governance.models import SecurityCommittee
    from core.audit import AuditLog
    client, _ = co
    body = SecurityCommittee.objects.create(name="CdA", committee_type="cda")
    client.post(URL_MEMBERS, {"committee": str(body.id), "full_name": "Paola Neri",
                              "valid_from": "2025-01-01"}, format="json")
    log = AuditLog.objects.filter(action_code="governance.committee_member.create").latest("timestamp_utc")
    assert "Paola" not in str(log.payload)
