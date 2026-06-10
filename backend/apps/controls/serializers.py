from rest_framework import serializers

from .models import Control, ControlDomain, ControlInstance, Framework


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = "__all__"


class ControlDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlDomain
        fields = "__all__"


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = "__all__"


class ControlInstanceSerializer(serializers.ModelSerializer):
    control_external_id = serializers.CharField(source="control.external_id", read_only=True)
    control_title = serializers.SerializerMethodField()
    framework_code = serializers.CharField(source="control.framework.code", read_only=True)
    mapped_controls = serializers.SerializerMethodField()
    suggested_status = serializers.SerializerMethodField(read_only=True)
    suggestion_differs = serializers.SerializerMethodField(read_only=True)
    calc_maturity_level = serializers.SerializerMethodField(read_only=True)
    owner_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ControlInstance
        fields = "__all__"
        # I campi governati dai service NON sono scrivibili via PATCH/PUT generica:
        # passare dagli endpoint dedicati, che validano e scrivono l'audit trail
        # (regola architetturale #2 — business logic solo nei services).
        #   status / last_evaluated_*          → POST /evaluate/ (evaluate_control)
        #   applicability / exclusion / na_*   → POST /set-applicability/
        #   maturity_level{,_override}         → POST /set-maturity/
        #   approved_in_soa / soa_*            → POST /bulk-approve-soa/
        #   needs_revaluation{,_since}         → cascata change asset + evaluate
        # Scrivibili via PATCH restano solo: owner, notes, assets (con
        # validate_assets), documents/evidences (equivalenti a link/unlink).
        read_only_fields = [
            "status",
            "last_evaluated_at",
            "last_evaluated_note",
            "applicability",
            "exclusion_justification",
            "na_justification",
            "na_approved_by",
            "na_second_approver",
            "na_approved_at",
            "na_review_by",
            "maturity_level",
            "maturity_level_override",
            "approved_in_soa",
            "soa_approved_at",
            "soa_approved_by",
            "needs_revaluation",
            "needs_revaluation_since",
            "created_at",
            "updated_at",
            "created_by",
            "deleted_at",
        ]

    def validate_assets(self, value):
        """Gli asset collegati devono appartenere allo stesso plant del controllo
        (P1-5): il legame restringe la cascata di rivalutazione per-plant, quindi
        un asset di un altro plant non avrebbe senso e violerebbe lo scope."""
        plant = self.instance.plant if self.instance else self.initial_data.get("plant")
        plant_id = getattr(plant, "id", plant)
        if plant_id and value:
            foreign = [a for a in value if str(a.plant_id) != str(plant_id)]
            if foreign:
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    "Gli asset collegati devono appartenere allo stesso plant del controllo."
                )
        return value

    def get_control_title(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", None) if request else None
        return obj.control.get_title(lang or "it")

    def get_suggested_status(self, obj):
        from .services import calc_suggested_status
        return calc_suggested_status(obj)

    def get_suggestion_differs(self, obj):
        from .services import calc_suggested_status
        return calc_suggested_status(obj) != obj.status

    def get_calc_maturity_level(self, obj):
        return obj.calc_maturity_level

    def get_owner_display(self, obj):
        if not obj.owner:
            return None
        return (
            f"{obj.owner.first_name} {obj.owner.last_name}".strip()
            or obj.owner.email
        )

    def get_mapped_controls(self, obj):
        result = []
        for m in obj.control.mappings_from.all():
            result.append({
                "external_id": m.target_control.external_id,
                "framework_code": m.target_control.framework.code,
                "relationship": m.relationship,
            })
        for m in obj.control.mappings_to.all():
            result.append({
                "external_id": m.source_control.external_id,
                "framework_code": m.source_control.framework.code,
                "relationship": m.relationship,
            })
        return result

