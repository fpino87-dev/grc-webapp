"""
Signal handlers per auth_grc (newfix S8).

Quando la password di un utente viene cambiata (admin reset, self-service,
script di rotazione), TUTTI i TrustedDevice dell'utente vengono revocati:
un attaccante che possedeva un device_token rubato perde immediatamente
il bypass MFA. Conforme a ISO 27001 A.9.2.4 (gestione segreti) e
A.9.4.3 (sistema di gestione password).
"""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


_PASSWORD_CHANGED_FLAG = "_grc_password_changed"


@receiver(pre_save, sender=get_user_model())
def _detect_password_change(sender, instance, **kwargs):
    """Marca l'istanza se la password e' cambiata rispetto al DB."""
    if not instance.pk:
        return
    try:
        old = sender.objects.only("password").get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.password != instance.password:
        setattr(instance, _PASSWORD_CHANGED_FLAG, True)


@receiver(post_save, sender=get_user_model())
def _revoke_trusted_devices_on_password_change(sender, instance, created, **kwargs):
    if created or not getattr(instance, _PASSWORD_CHANGED_FLAG, False):
        return
    # Import locale per evitare app loading order issues.
    from apps.auth_grc.models import TrustedDevice
    revoked = TrustedDevice.revoke_all_for_user(instance)
    setattr(instance, _PASSWORD_CHANGED_FLAG, False)

    if revoked:
        try:
            from core.audit import log_action
            log_action(
                user=None,
                action_code="AUTH_PASSWORD_CHANGED_DEVICES_REVOKED",
                level="L2",
                entity=instance,
                payload={"trusted_devices_revoked": revoked, "user_id": instance.pk},
            )
        except Exception:
            # Audit best-effort: la revoca e' gia' avvenuta.
            pass
