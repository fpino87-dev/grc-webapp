from rest_framework import serializers

from .models import BusinessUnit, Plant, PlantFramework


class BusinessUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUnit
        fields = "__all__"


class PlantSerializer(serializers.ModelSerializer):
    # Esplicito per accettare campo assente/vuoto → default Europe/Rome
    timezone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Plant
        fields = "__all__"

    def validate_timezone(self, value):
        import zoneinfo

        from django.utils.translation import gettext as _

        if value and value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(
                _("Timezone IANA non valido: %(tz)s") % {"tz": value}
            )
        return value or "Europe/Rome"


class PlantFrameworkSerializer(serializers.ModelSerializer):
    framework_code = serializers.CharField(source="framework.code", read_only=True)
    framework_name = serializers.CharField(source="framework.name", read_only=True)

    class Meta:
        model = PlantFramework
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "active_from"]

