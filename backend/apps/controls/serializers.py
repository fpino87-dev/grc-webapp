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
    soa_approved_by_name = serializers.SerializerMethodField(read_only=True)
    can_propagate = serializers.SerializerMethodField(read_only=True)

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

    def validate_owner(self, value):
        """L'owner deve avere accesso al plant del controllo (C9): senza questo
        controllo lato server il filtro della tendina UI sarebbe aggirabile via
        PATCH diretta, assegnando un controllo a chi non ha accesso al sito."""
        if value is None:
            return value
        plant = self.instance.plant if self.instance else self.initial_data.get("plant")
        if plant is not None and not hasattr(plant, "bu_id"):
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant).first()
        if plant is not None:
            from apps.auth_grc.services import user_has_plant_access
            if not user_has_plant_access(value, plant):
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    "L'owner deve avere accesso al plant del controllo."
                )
        return value

    def get_control_title(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", None) if request else None
        return obj.control.get_title(lang or "it")

    def _suggested_status(self, obj):
        # Memoizzato per istanza: suggested_status e suggestion_differs lo
        # condividono, e calc_suggested_status percorre documenti/evidenze (C2)
        cache = self.context.setdefault("_suggested_status_cache", {})
        if obj.pk not in cache:
            from .services import calc_suggested_status
            cache[obj.pk] = calc_suggested_status(obj)
        return cache[obj.pk]

    def get_suggested_status(self, obj):
        return self._suggested_status(obj)

    def get_suggestion_differs(self, obj):
        return self._suggested_status(obj) != obj.status

    def get_calc_maturity_level(self, obj):
        return obj.calc_maturity_level

    def get_owner_display(self, obj):
        if not obj.owner:
            return None
        return (
            f"{obj.owner.first_name} {obj.owner.last_name}".strip()
            or obj.owner.email
        )

    def get_soa_approved_by_name(self, obj):
        if not obj.soa_approved_by:
            return None
        u = obj.soa_approved_by
        return f"{u.first_name} {u.last_name}".strip() or u.email or u.username

    def get_can_propagate(self, obj):
        """True solo se "⇒ propaga" farebbe davvero qualcosa: stato propagabile
        E almeno un controllo mappato con la relazione/direzione giusta che ha
        un'istanza in questo plant. Col crosswalk C12 quasi ogni controllo ha
        mapping, ma senza un target istanziato il pulsante produceva solo
        "✓ 0" — la UI lo mostra solo quando questo flag è True.

        Stesse regole di propagate_control: niente query per riga — i mapping
        sono prefetchati, le istanze del plant sono una query cached (C2)."""
        from .services.instances import _PROPAGABLE_RELATIONSHIPS, _PROPAGABLE_STATUSES

        if obj.status not in _PROPAGABLE_STATUSES:
            return False
        candidate_ids = {
            m.target_control_id
            for m in obj.control.mappings_from.all()
            if m.relationship in _PROPAGABLE_RELATIONSHIPS
        } | {
            m.source_control_id
            for m in obj.control.mappings_to.all()
            if m.relationship == "equivalente"  # simmetrica; covers no
        }
        candidate_ids.discard(obj.control_id)
        if not candidate_ids:
            return False
        cache = self.context.setdefault("_plant_control_ids_cache", {})
        if obj.plant_id not in cache:
            cache[obj.plant_id] = set(
                ControlInstance.objects.filter(
                    plant_id=obj.plant_id, deleted_at__isnull=True,
                ).values_list("control_id", flat=True)
            )
        return bool(candidate_ids & cache[obj.plant_id])

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

