from rest_framework import serializers

from .models import BusinessUnit, Plant, PlantFramework


_HYGIENE_READ_ONLY = ["created_by", "created_at", "updated_at", "deleted_at"]


class BusinessUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUnit
        fields = "__all__"
        read_only_fields = _HYGIENE_READ_ONLY


class PlantSerializer(serializers.ModelSerializer):
    # Esplicito per accettare campo assente/vuoto → default Europe/Rome
    timezone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Plant
        fields = "__all__"
        read_only_fields = _HYGIENE_READ_ONLY

    def validate_timezone(self, value):
        import zoneinfo

        from django.utils.translation import gettext as _

        if value and value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(
                _("Timezone IANA non valido: %(tz)s") % {"tz": value}
            )
        return value or "Europe/Rome"

    def validate_parent_plant(self, value):
        # DRF non invoca Plant.clean(): replichiamo qui il vincolo "max 1 livello
        # di nesting" (un sub-plant non può a sua volta avere un parent).
        from django.utils.translation import gettext as _

        if value is not None and value.parent_plant_id is not None:
            raise serializers.ValidationError(
                _("Max 1 livello di nesting per i sub-plant: il sito scelto è già un sotto-sito.")
            )
        return value


class PlantFrameworkSerializer(serializers.ModelSerializer):
    framework_code = serializers.CharField(source="framework.code", read_only=True)
    framework_name = serializers.CharField(source="framework.name", read_only=True)

    class Meta:
        model = PlantFramework
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "active_from"]

