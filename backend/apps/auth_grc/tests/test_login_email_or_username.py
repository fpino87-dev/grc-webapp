"""
Accesso con username oppure con email.

La pagina di login chiede «Email / Username», ma gli utenti hanno uno username
distinto dall'email e l'autenticazione guardava solo lo username: chi digitava
l'email riceveva «credenziali non valide».
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.audit import AuditLog

User = get_user_model()
pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd-2026!"
URL = "/api/token/"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="mrossi", email="Mario.Rossi@azienda.it", password=PASSWORD,
    )


def _login(identifier, password=PASSWORD):
    return APIClient().post(URL, {"username": identifier, "password": password})


def test_login_with_username(user):
    assert _login("mrossi").status_code == 200


@pytest.mark.parametrize("identifier", [
    "Mario.Rossi@azienda.it",
    "mario.rossi@azienda.it",      # l'email non distingue le maiuscole
    "  mario.rossi@azienda.it ",   # spazi da copia-incolla
])
def test_login_with_email(user, identifier):
    res = _login(identifier)
    assert res.status_code == 200
    assert "access" in res.data


def test_wrong_password_is_refused_and_audited_for_both_identifiers(user):
    assert _login("mario.rossi@azienda.it", "sbagliata").status_code == 401
    assert _login("mrossi", "sbagliata").status_code == 401
    assert AuditLog.objects.filter(action_code="auth.login.failure", entity_id=user.pk).count() == 2


def test_unknown_email_is_refused_without_audit(user):
    assert _login("nessuno@azienda.it").status_code == 401
    assert not AuditLog.objects.filter(action_code="auth.login.failure").exists()


def test_inactive_user_cannot_login_with_email(user):
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert _login("mario.rossi@azienda.it").status_code == 401


def test_email_shared_by_two_accounts_is_refused_but_username_still_works(user):
    User.objects.create_user(username="mrossi2", email="mario.rossi@azienda.it", password=PASSWORD)
    assert _login("mario.rossi@azienda.it").status_code == 401
    assert _login("mrossi").status_code == 200


def test_username_takes_precedence_over_another_users_email(user):
    """Uno username uguale all'email di un altro utente resta di chi lo possiede."""
    User.objects.create_user(
        username="mario.rossi@azienda.it", email="altro@azienda.it", password="Altr4-Passw0rd-2026!",
    )
    assert _login("mario.rossi@azienda.it", "Altr4-Passw0rd-2026!").status_code == 200
    assert _login("mario.rossi@azienda.it", PASSWORD).status_code == 401


# ── Email unica: serve anche per accedere ───────────────────────────────────

USERS_URL = "/api/v1/auth/users/"


@pytest.fixture
def admin_client(db):
    admin = User.objects.create_superuser(username="root", email="root@azienda.it", password=PASSWORD)
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


def test_new_user_cannot_reuse_an_existing_email(admin_client, user):
    resp = admin_client.post(USERS_URL, {
        "username": "mrossi-bis", "email": "MARIO.ROSSI@azienda.it", "password": PASSWORD,
    }, format="json")
    assert resp.status_code == 400
    assert "email" in resp.data
    assert not User.objects.filter(username="mrossi-bis").exists()


def test_user_email_cannot_be_changed_to_one_in_use_but_own_email_is_kept(admin_client, user):
    other = User.objects.create_user(username="lbianchi", email="l.bianchi@azienda.it", password=PASSWORD)
    resp = admin_client.patch(f"{USERS_URL}{other.pk}/", {"email": "mario.rossi@azienda.it"}, format="json")
    assert resp.status_code == 400
    resp = admin_client.patch(
        f"{USERS_URL}{other.pk}/", {"email": "l.bianchi@azienda.it", "first_name": "Luca"}, format="json",
    )
    assert resp.status_code == 200
