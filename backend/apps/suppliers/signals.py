"""
Signals per il modulo Fornitori.

Ricalcola automaticamente `risk_adj` quando cambiano i campi che lo determinano:
  - `nis2_relevant`
  - `supply_concentration_pct` (via property `concentration_threshold`)

Nota: il ricalcolo innescato da modifiche alla valutazione interna o all'assessment
avviene nei service (`create_internal_evaluation`, `approve_assessment`), non qui,
per evitare ricorsione sul save.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Supplier


_NIS2_FIELDS = ("nis2_relevant", "supply_concentration_pct")


@receiver(pre_save, sender=Supplier)
def mark_supplier_for_risk_recompute(sender, instance: Supplier, **kwargs):
    """
    Marca l'istanza con un flag interno se i campi NIS2/concentrazione sono cambiati.
    Il ricalcolo effettivo viene eseguito dal post_save.
    """
    if not instance.pk:
        instance._risk_adj_needs_recompute = False
        return
    try:
        old = Supplier.objects.only(*_NIS2_FIELDS).get(pk=instance.pk)
    except Supplier.DoesNotExist:
        instance._risk_adj_needs_recompute = False
        return
    changed = any(
        getattr(old, f) != getattr(instance, f) for f in _NIS2_FIELDS
    )
    instance._risk_adj_needs_recompute = changed


from django.db.models.signals import post_save


@receiver(post_save, sender=Supplier)
def recompute_risk_adj_on_nis2_change(sender, instance: Supplier, created, **kwargs):
    if created:
        return
    if not getattr(instance, "_risk_adj_needs_recompute", False):
        return
    # Evita ricorsione: il recompute farà ancora save, ma il pre_save vedrà
    # i campi NIS2 invariati e non marcherà il flag.
    instance._risk_adj_needs_recompute = False
    from .risk_adj import recompute_risk_adj
    recompute_risk_adj(instance)
