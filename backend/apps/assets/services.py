from .models import Asset, AssetIT, AssetOT


def get_assets_by_plant(plant_id):
    return Asset.objects.filter(plant_id=plant_id).select_related("plant", "owner")


def get_eol_assets():
    from django.utils import timezone

    return AssetIT.objects.filter(eol_date__lte=timezone.now().date()).select_related("plant")


def get_critical_assets(plant_id):
    return Asset.objects.filter(plant_id=plant_id, criticality__gte=4).select_related("plant", "owner")
