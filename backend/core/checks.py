"""Deployment checks for application-specific secrets."""

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.checks import Error, register


@register(deploy=True)
def production_secrets(app_configs, **kwargs):
    errors = []
    if len(settings.SECRET_KEY) < 50 or "placeholder" in settings.SECRET_KEY.lower():
        errors.append(Error("Use a random SECRET_KEY of at least 50 characters.", id="grc.E001"))
    try:
        Fernet(settings.FERNET_KEYS[0])
    except (ValueError, TypeError, IndexError):
        errors.append(Error("Configure a valid FERNET_KEY.", id="grc.E002"))
    backup_key = settings.BACKUP_ENCRYPTION_KEY
    if len(backup_key) < 32 or backup_key in settings.FERNET_KEYS or backup_key == settings.SECRET_KEY:
        errors.append(Error("Configure a separate random BACKUP_ENCRYPTION_KEY (32+ characters).", id="grc.E003"))
    if "*" in settings.ALLOWED_HOSTS:
        errors.append(Error("Specify explicit ALLOWED_HOSTS in production.", id="grc.E004"))
    return errors
