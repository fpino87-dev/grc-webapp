from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone


def _touch_instance(instance):
    if hasattr(instance, "updated_at"):
        instance.updated_at = timezone.now()
        instance.save(update_fields=["updated_at"])


@receiver(m2m_changed, sender="documents.Document_control_refs")
def on_documents_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _touch_instance(instance)


@receiver(m2m_changed, sender="controls.ControlInstance_evidences")
def on_evidences_changed(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _touch_instance(instance)
