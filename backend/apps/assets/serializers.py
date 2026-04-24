from rest_framework import serializers

from .models import Asset, AssetDependency, AssetIT, AssetOT, AssetSW, NetworkZone


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


class AssetITSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "plant_name", "owner_username", "asset_type"]


class AssetOTSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    network_zone_name = serializers.CharField(source="network_zone.name", read_only=True)
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
            "notes",
            "processes",
            "purdue_level",
            "category",
            "patchable",
            "patch_block_reason",
            "maintenance_window",
            "network_zone",
            "network_zone_name",
            "vendor",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "plant_name", "owner_username", "network_zone_name", "asset_type"]


class AssetSWSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "plant_name", "owner_username", "asset_type", "is_eos", "days_to_eos"]


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
