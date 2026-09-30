"""Backend di autenticazione: accesso con username oppure con email."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def find_login_user(identifier: str):
    """Utente a cui si riferisce l'identificativo digitato al login: username
    esatto, altrimenti email (senza distinzione di maiuscole) se appartiene a
    un solo utente. None se non esiste o se l'email è ambigua."""
    User = get_user_model()
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    user = User._default_manager.filter(**{User.USERNAME_FIELD: identifier}).first()
    if user is not None:
        return user
    if "@" not in identifier:
        return None
    matches = list(User._default_manager.filter(email__iexact=identifier)[:2])
    return matches[0] if len(matches) == 1 else None


class EmailOrUsernameBackend(ModelBackend):
    """Come `ModelBackend`, ma accetta anche l'email al posto dello username.

    La pagina di accesso chiede «Email / Username» e gli utenti hanno uno
    username distinto dall'email: con il solo `ModelBackend` l'email veniva
    rifiutata come credenziale errata.

    - lo username ha la precedenza (comportamento invariato per chi lo usa);
    - l'email vale solo se appartiene a un unico utente: con due account sulla
      stessa email non si sceglie a caso, si rifiuta (resta lo username);
    - il costo dell'hash della password viene pagato anche quando l'utente non
      esiste, come fa Django, per non rivelare dai tempi di risposta quali
      email sono registrate.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        user = find_login_user(username)
        if user is None:
            User().set_password(password)  # tempo costante rispetto all'utente esistente
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
