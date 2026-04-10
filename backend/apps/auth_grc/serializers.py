from rest_framework import serializers

from .models import ExternalAuditorToken, RoleCompetencyRequirement, UserCompetency, UserPlantAccess


class UserPlantAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlantAccess
        fields = "__all__"


class ExternalAuditorTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAuditorToken
        fields = "__all__"


class RoleCompetencyRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleCompetencyRequirement
        fields = "__all__"


class UserCompetencySerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    verified_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserCompetency
        fields = "__all__"

    def get_verified_by_name(self, obj):
        if not obj.verified_by:
            return None
        u = obj.verified_by
        return f"{u.first_name} {u.last_name}".strip() or u.email

