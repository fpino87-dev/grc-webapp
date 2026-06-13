"""Mixin riusabili per i ViewSet DRF della piattaforma."""
from rest_framework.response import Response

from core.audit import log_action


class SoftDeleteAuditMixin:
    """`perform_destroy` → soft delete + audit, invece dell'hard delete di DRF.

    `BaseModel` non override `delete()`, quindi il `DestroyModelMixin` di default
    cancella FISICAMENTE la riga e non scrive alcun audit, violando le regole #5
    (soft delete sempre) e #3 (audit sulle azioni rilevanti). Le sottoclassi
    impostano `audit_action` (es. ``"plants.business_unit"``); in mancanza si
    deriva da app_label/model_name del modello.
    """

    audit_action: str | None = None

    def perform_destroy(self, instance):
        instance.soft_delete()
        action = self.audit_action or f"{instance._meta.app_label}.{instance._meta.model_name}"
        log_action(
            user=getattr(self.request, "user", None),
            action_code=f"{action}.delete",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )


# Risposta 204 standard riusata dove serve costruirla a mano.
NO_CONTENT = Response(status=204)
