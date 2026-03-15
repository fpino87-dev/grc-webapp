from django.utils import timezone

from core.audit import log_action

from .models import Asset, AssetIT, AssetOT


def get_assets_by_plant(plant_id):
    return Asset.objects.filter(plant_id=plant_id).select_related("plant", "owner")


def get_eol_assets():
    return AssetIT.objects.filter(eol_date__lte=timezone.now().date()).select_related("plant")


def get_critical_assets(plant_id):
    return Asset.objects.filter(plant_id=plant_id, criticality__gte=4).select_related("plant", "owner")


def register_change(asset, user, change_ref: str,
                    change_desc: str = "",
                    portal_url: str = "") -> dict:
    """
    Registra un change esterno sull'asset.
    Non gestisce il workflow del change — solo lo referenzia.
    Propaga automaticamente flag "da rivalutare" a:
      - ControlInstance collegati al processo BIA dell'asset
      - RiskAssessment collegati all'asset
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

    # Propaga a ControlInstance collegati tramite processi BIA
    from apps.controls.models import ControlInstance
    for process in asset.processes.filter(deleted_at__isnull=True):
        affected["processes"] += 1
        cis = ControlInstance.objects.filter(
            plant=asset.plant,
            deleted_at__isnull=True,
        ).exclude(status__in=["non_valutato", "gap"])
        for ci in cis:
            ci.needs_revaluation = True
            ci.needs_revaluation_since = today
            ci.save(update_fields=[
                "needs_revaluation", "needs_revaluation_since", "updated_at",
            ])
            affected["controls"] += 1

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

    # Pulisce anche i flag sui controlli collegati
    from apps.controls.models import ControlInstance
    threshold_date = asset.last_change_date if asset.last_change_date else today
    ControlInstance.objects.filter(
        plant=asset.plant,
        needs_revaluation=True,
        needs_revaluation_since__lte=threshold_date,
        deleted_at__isnull=True,
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
