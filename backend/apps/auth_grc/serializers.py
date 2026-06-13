from rest_framework import serializers

from .models import ExternalAuditorToken, RoleCompetencyRequirement, UserCompetency, UserPlantAccess


class UserPlantAccessSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    role_label = serializers.SerializerMethodField(read_only=True)
    scope_plant_codes = serializers.SerializerMethodField(read_only=True)
    scope_bu_code = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserPlantAccess
        fields = "__all__"
        read_only_fields = ["created_by", "created_at", "updated_at", "deleted_at"]

    def get_user_name(self, obj):
        u = obj.user
        if not u:
            return None
        return f"{u.first_name} {u.last_name}".strip() or u.email or u.username

    def get_role_label(self, obj):
        from .models import GrcRole
        try:
            return str(GrcRole(obj.role).label)
        except ValueError:
            return obj.role

    def get_scope_plant_codes(self, obj):
        return list(obj.scope_plants.values_list("code", flat=True))

    def get_scope_bu_code(self, obj):
        return obj.scope_bu.code if obj.scope_bu_id else None

    def validate(self, attrs):
        """Un perimetro per-sito/BU senza i relativi siti/BU creerebbe un accesso
        VUOTO (get_user_plant_ids → set vuoto): l'utente non vedrebbe nulla. La
        UI permetteva solo 'org'; ora che si assegna per-sito va validato."""
        from django.utils.translation import gettext as _

        scope_type = attrs.get("scope_type") or getattr(self.instance, "scope_type", None)
        if scope_type in ("plant_list", "single_plant"):
            plants = attrs.get("scope_plants")
            if plants is None and self.instance:
                plants = list(self.instance.scope_plants.all())
            if not plants:
                raise serializers.ValidationError(
                    {"scope_plants": _("Seleziona almeno un sito per questo perimetro.")}
                )
        if scope_type == "bu":
            bu = attrs.get("scope_bu") if "scope_bu" in attrs else getattr(self.instance, "scope_bu", None)
            if not bu:
                raise serializers.ValidationError(
                    {"scope_bu": _("Seleziona una Business Unit per questo perimetro.")}
                )
        return attrs


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

