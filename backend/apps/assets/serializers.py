from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import (
    Asset,
    AssetDependency,
    AssetFacility,
    AssetIT,
    AssetOT,
    AssetSW,
    NetworkZone,
)


# ── Manutenzione periodica ───────────────────────────────────────────────────
# Campi comuni a tutti i tipi di asset. La cadenza è configurazione e si
# scrive normalmente; data ed esito dell'ultima manutenzione li governa il
# service (azione `record-maintenance`), che scrive anche l'audit trail.
MAINTENANCE_FIELDS = [
    "maintenance_frequency_months",
    "last_maintenance_date",
    "next_maintenance_date",
    "last_maintenance_result",
    "maintenance_notes",
    "maintenance_is_overdue",
]
MAINTENANCE_READ_ONLY = [
    "last_maintenance_date",
    "next_maintenance_date",
    "last_maintenance_result",
    "maintenance_notes",
    "maintenance_is_overdue",
]


class MaintenanceScheduleMixin:
    """Cambiare la cadenza ricalcola subito la prossima scadenza: senza, il
    nuovo intervallo sarebbe visibile nel form ma lo scadenzario continuerebbe
    a mostrare la data vecchia fino alla manutenzione successiva."""

    maintenance_is_overdue = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        from .services import apply_maintenance_schedule

        instance = super().create(validated_data)
        if instance.maintenance_frequency_months:
            apply_maintenance_schedule(instance)
        return instance

    def update(self, instance, validated_data):
        from .services import apply_maintenance_schedule

        before = instance.maintenance_frequency_months
        instance = super().update(instance, validated_data)
        if instance.maintenance_frequency_months != before:
            apply_maintenance_schedule(instance, base=instance.last_maintenance_date)
        return instance


class NetworkZoneSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)

    class Meta:
        model = NetworkZone
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "zone_type",
            "purdue_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "plant_name"]


class AssetITSerializer(MaintenanceScheduleMixin, serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    maintainer_supplier_name = serializers.CharField(source="maintainer_supplier.name", read_only=True)
    processes = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=Asset._meta.get_field("processes").remote_field.model.objects.all(),
        required=False,
    )

    class Meta:
        model = AssetIT
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "asset_type",
            "criticality",
            "owner",
            "owner_username",
            "maintainer_supplier",
            "maintainer_supplier_name",
            "notes",
            "processes",
            "fqdn",
            "ip_address",
            "os",
            "eol_date",
            "cve_score_max",
            "internet_exposed",
            "deployment_type",
            "provider",
            "service_name",
            "data_classification",
            *MAINTENANCE_FIELDS,
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "plant_name", "owner_username",
            "asset_type", *MAINTENANCE_READ_ONLY,
        ]


class AssetOTSerializer(MaintenanceScheduleMixin, serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    network_zone_name = serializers.CharField(source="network_zone.name", read_only=True)
    maintainer_supplier_name = serializers.CharField(source="maintainer_supplier.name", read_only=True)
    processes = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=Asset._meta.get_field("processes").remote_field.model.objects.all(),
        required=False,
    )

    class Meta:
        model = AssetOT
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "asset_type",
            "criticality",
            "owner",
            "owner_username",
            "maintainer_supplier",
            "maintainer_supplier_name",
            "notes",
            "processes",
            "fqdn",
            "ip_address",
            "internet_exposed",
            "purdue_level",
            "category",
            "patchable",
            "patch_block_reason",
            "maintenance_window",
            "network_zone",
            "network_zone_name",
            "vendor",
            *MAINTENANCE_FIELDS,
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "plant_name", "owner_username",
            "network_zone_name", "asset_type", *MAINTENANCE_READ_ONLY,
        ]


class AssetSWSerializer(MaintenanceScheduleMixin, serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    is_eos = serializers.BooleanField(read_only=True)
    days_to_eos = serializers.IntegerField(read_only=True)
    processes = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=Asset._meta.get_field("processes").remote_field.model.objects.all(),
        required=False,
    )

    class Meta:
        model = AssetSW
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "asset_type",
            "criticality",
            "owner",
            "owner_username",
            "notes",
            "processes",
            "vendor",
            "version",
            "approval_status",
            "license_type",
            "end_of_support",
            "external_ref",
            "vendor_url",
            "is_eos",
            "days_to_eos",
            *MAINTENANCE_FIELDS,
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "plant_name", "owner_username",
            "asset_type", "is_eos", "days_to_eos", *MAINTENANCE_READ_ONLY,
        ]


class AssetFacilitySerializer(MaintenanceScheduleMixin, serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    maintainer_supplier_name = serializers.CharField(
        source="maintainer_supplier.name", read_only=True
    )
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = AssetFacility
        fields = [
            "id",
            "plant",
            "plant_name",
            "name",
            "asset_type",
            "category",
            "category_display",
            "criticality",
            "owner",
            "owner_username",
            "maintainer_supplier",
            "maintainer_supplier_name",
            "location",
            "vendor",
            "model",
            "serial_number",
            "installation_date",
            "rated_autonomy_minutes",
            "serves_assets",
            "notes",
            *MAINTENANCE_FIELDS,
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "plant_name", "owner_username",
            "maintainer_supplier_name", "category_display", "asset_type",
            *MAINTENANCE_READ_ONLY,
        ]

    def validate(self, attrs):
        """L'autonomia nominale ha senso solo dove esiste una batteria o un
        serbatoio: altrove è un numero che nessuno saprebbe interpretare."""
        category = attrs.get("category") or getattr(self.instance, "category", "")
        autonomy = attrs.get("rated_autonomy_minutes")
        if autonomy and category not in ("ups", "gruppo_elettrogeno"):
            raise serializers.ValidationError({
                "rated_autonomy_minutes": _(
                    "L'autonomia nominale si applica solo a UPS e gruppi elettrogeni."
                )
            })
        return attrs


class AssetDependencySerializer(serializers.ModelSerializer):
    from_asset_name = serializers.CharField(source="from_asset.name", read_only=True)
    to_asset_name = serializers.CharField(source="to_asset.name", read_only=True)

    class Meta:
        model = AssetDependency
        fields = [
            "id",
            "from_asset",
            "from_asset_name",
            "to_asset",
            "to_asset_name",
            "dep_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "from_asset_name", "to_asset_name"]
