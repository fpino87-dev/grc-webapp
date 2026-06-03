from django.db import transaction
from django.utils import timezone

from core.audit import log_action

from .models import Asset, AssetDependency, AssetIT, AssetOT


def get_assets_by_plant(plant_id):
    return Asset.objects.filter(plant_id=plant_id).select_related("plant", "owner")


def get_eol_assets():
    return AssetIT.objects.filter(eol_date__lte=timezone.now().date()).select_related("plant")


def get_critical_assets(plant_id):
    return Asset.objects.filter(plant_id=plant_id, criticality__gte=4).select_related("plant", "owner")


def _impacted_control_instances(asset):
    """ControlInstance impattati da un change sull'`asset`, con il loro scope.

    Se l'asset ha controlli esplicitamente collegati (M2M `ControlInstance.assets`)
    restringe a quelli (scope "asset"); altrimenti ricade su tutti i controlli del
    plant (scope "plant", comportamento storico) finché i legami non sono popolati.
    Ritorna `(queryset, narrowed: bool)` — `narrowed=True` se ha usato il legame
    diretto. Filtra sempre i soft-deleted.
    """
    from apps.controls.models import ControlInstance

    linked = ControlInstance.objects.filter(assets=asset, deleted_at__isnull=True)
    if linked.exists():
        return linked, True
    return ControlInstance.objects.filter(plant=asset.plant, deleted_at__isnull=True), False


@transaction.atomic
def register_change(asset, user, change_ref: str,
                    change_desc: str = "",
                    portal_url: str = "") -> dict:
    """
    Registra un change esterno sull'asset.
    Non gestisce il workflow del change — solo lo referenzia.
    Propaga automaticamente flag "da rivalutare" a:
      - ControlInstance del plant (compliant/parziale/na) — aggancio a livello
        plant: ControlInstance non ha ancora un legame diretto con asset/processo
        (vedi budnewsfix P1 per il narrowing);
      - RiskAssessment collegati all'asset.
    Atomico: o si aggiornano asset + cascate + audit insieme, o niente.
    """
    asset.last_change_ref = change_ref
    asset.last_change_date = timezone.now().date()
    asset.last_change_desc = change_desc
    asset.change_portal_url = portal_url
    asset.needs_revaluation = True
    asset.needs_revaluation_since = timezone.now().date()
    asset.save(update_fields=[
        "last_change_ref", "last_change_date", "last_change_desc",
        "change_portal_url", "needs_revaluation",
        "needs_revaluation_since", "updated_at",
    ])

    affected = {
        "controls": 0,
        "risks": 0,
        "processes": 0,
    }

    today = timezone.now().date()

    # Numero di processi BIA in cui l'asset è coinvolto (solo conteggio).
    affected["processes"] = asset.processes.filter(deleted_at__isnull=True).count()

    # Propaga ai ControlInstance che dichiaravano conformità (compliant/parziale/
    # na) → li rimette "da rivalutare". Se l'asset ha controlli esplicitamente
    # collegati (M2M ControlInstance.assets) restringe a quelli; altrimenti
    # fallback plant-wide (comportamento storico). UNA sola volta.
    impacted_qs, narrowed = _impacted_control_instances(asset)
    cis = list(impacted_qs.exclude(status__in=["non_valutato", "gap"]))
    for ci in cis:
        ci.needs_revaluation = True
        ci.needs_revaluation_since = today
        ci.save(update_fields=[
            "needs_revaluation", "needs_revaluation_since", "updated_at",
        ])
    affected["controls"] = len(cis)
    affected["controls_scope"] = "asset" if narrowed else "plant"

    # Propaga a RiskAssessment collegati all'asset
    from apps.risk.models import RiskAssessment
    risks = RiskAssessment.objects.filter(
        asset=asset,
        status="completato",
        deleted_at__isnull=True,
    )
    for ra in risks:
        ra.needs_revaluation = True
        ra.needs_revaluation_since = today
        ra.save(update_fields=[
            "needs_revaluation", "needs_revaluation_since", "updated_at",
        ])
        affected["risks"] += 1

    log_action(
        user=user,
        action_code="asset.change_registered",
        level="L2",
        entity=asset,
        payload={
            "change_ref": change_ref,
            "change_desc": change_desc[:100],
            "affected_controls": affected["controls"],
            "affected_risks": affected["risks"],
            "controls_scope": affected["controls_scope"],
        },
    )
    return {
        "ok": True,
        "asset": asset.name,
        "ref": change_ref,
        "affected": affected,
    }


def clear_revaluation_flag(asset, user, notes: str = "") -> None:
    """
    Segna l'asset come rivalutato dopo un change.
    Chiama questo dopo aver verificato controlli e rischi.
    """
    today = timezone.now().date()
    asset.needs_revaluation = False
    asset.needs_revaluation_since = None
    asset.save(update_fields=[
        "needs_revaluation", "needs_revaluation_since", "updated_at"
    ])

    # Pulisce i flag sui controlli impattati dallo stesso change (stesso scope del
    # flagging: solo i controlli collegati all'asset se il legame esiste, altrimenti
    # plant-wide). Così "rivalutato" non azzera per sbaglio controlli di altri asset.
    threshold_date = asset.last_change_date if asset.last_change_date else today
    impacted_qs, _narrowed = _impacted_control_instances(asset)
    impacted_qs.filter(
        needs_revaluation=True,
        needs_revaluation_since__lte=threshold_date,
    ).update(
        needs_revaluation=False,
        needs_revaluation_since=None,
        updated_at=timezone.now(),
    )

    log_action(
        user=user,
        action_code="asset.revaluation_cleared",
        level="L2",
        entity=asset,
        payload={"notes": notes[:100]},
    )


@transaction.atomic
def delete_asset(asset: Asset, user) -> None:
    """
    Soft delete di un asset IT/OT. Bloccato se esistono rischi o dipendenze attive.

    Atomica: lo scollegamento dei processi (M2M), il soft-delete e l'audit log devono
    committarsi insieme (i controlli di blocco a monte sollevano ValidationError prima
    di qualsiasi scrittura, quindi non lasciano stato parziale).
    """
    from django.core.exceptions import ValidationError
    from django.db.models import Q
    from django.utils.translation import gettext as _

    from apps.risk.models import RiskAssessment, RiskScenario

    if RiskAssessment.objects.filter(asset=asset, deleted_at__isnull=True).exclude(
        status="archiviato"
    ).exists():
        raise ValidationError(
            _("Impossibile eliminare: esistono valutazioni rischio attive collegate all'asset.")
        )

    if RiskScenario.objects.filter(asset=asset, deleted_at__isnull=True).exists():
        raise ValidationError(
            _("Impossibile eliminare: esistono scenari di rischio collegati all'asset.")
        )

    if AssetDependency.objects.filter(
        Q(from_asset=asset) | Q(to_asset=asset),
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError(
            _("Impossibile eliminare: rimuovere prima le dipendenze tra asset.")
        )

    asset.processes.clear()
    asset.soft_delete()

    log_action(
        user=user,
        action_code="assets.asset.delete",
        level="L2",
        entity=asset,
        payload={
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": asset.asset_type,
            "plant_id": str(asset.plant_id),
        },
    )
