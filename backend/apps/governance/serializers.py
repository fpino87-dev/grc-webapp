from django.utils.translation import gettext as _
from rest_framework import serializers


from .models import (
    DocumentWorkflowPolicy,
    RoleAssignment,
    RoleRequirement,
    CommitteeMember,
    SecurityCommittee,
    SecurityObjective,
    SecurityObjectiveMeasurement,
)


class RoleAssignmentSerializer(serializers.ModelSerializer):
    user_email  = serializers.SerializerMethodField(read_only=True)
    user_name   = serializers.SerializerMethodField(read_only=True)
    is_active   = serializers.SerializerMethodField(read_only=True)
    # Dati strutturati dello scope: la label localizzata la compone il frontend
    # (prima il serializer restituiva una stringa hardcoded in italiano → utenti
    # EN/FR/PL/TR vedevano testo IT). code/name sono None per scope org o se la
    # BU/Plant referenziata non esiste più.
    scope_code  = serializers.SerializerMethodField(read_only=True)
    scope_name  = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = RoleAssignment
        fields = "__all__"
        # Campi gestiti dal server / ciclo di vita: mai scrivibili dal client
        # (created_by lo imposta perform_create; deleted_at solo via soft_delete
        # con audit; terminate/replace gestiscono valid_until con audit).
        read_only_fields = ["created_by", "created_at", "updated_at", "deleted_at"]
        # Il vincolo uniq_open_role_assignment genererebbe un validator DRF con
        # messaggio generico in non_field_errors: doppioni e titolare unico li
        # controlla services.create_role_assignment, con messaggio sul ruolo.
        validators = []

    def get_user_email(self, obj):
        return obj.user.email if obj.user_id else None

    def get_user_name(self, obj):
        if not obj.user_id:
            return None
        return obj.user.get_full_name() or obj.user.email

    def get_is_active(self, obj):
        return obj.is_active

    def _scope_maps(self):
        """Mappe BU/Plant per id caricate UNA volta per richiesta (no N+1: le
        tabelle sono piccole). Cache condivisa tra le righe via self.context."""
        cache = self.context.setdefault("_scope_maps", {})
        if not cache:
            from apps.plants.models import BusinessUnit, Plant
            cache["bu"] = {str(b.id): b for b in BusinessUnit.objects.all()}
            cache["plant"] = {str(p.id): p for p in Plant.objects.all()}
        return cache

    def _scope_obj(self, obj):
        if not obj.scope_id or obj.scope_type not in ("bu", "plant"):
            return None
        return self._scope_maps()[obj.scope_type].get(str(obj.scope_id))

    def get_scope_code(self, obj):
        o = self._scope_obj(obj)
        return o.code if o else None

    def get_scope_name(self, obj):
        o = self._scope_obj(obj)
        return o.name if o else None


class RoleRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleRequirement
        fields = "__all__"
        read_only_fields = ["created_by", "created_at", "updated_at", "deleted_at"]


class DocumentWorkflowPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentWorkflowPolicy
        fields = "__all__"


class CommitteeMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_is_active = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = CommitteeMember
        fields = [
            "id", "committee", "full_name", "position", "body_role", "user",
            "user_name", "user_is_active", "valid_from", "valid_until", "is_active",
        ]
        read_only_fields = ["id"]

    def get_user_name(self, obj):
        if not obj.user_id:
            return None
        u = obj.user
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def get_user_is_active(self, obj):
        return obj.user.is_active if obj.user_id else None

    def get_is_active(self, obj):
        from django.utils import timezone
        return obj.is_active_on(timezone.localdate())


class SecurityCommitteeSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    plant_codes = serializers.SerializerMethodField()
    is_management_body = serializers.BooleanField(read_only=True)

    class Meta:
        model = SecurityCommittee
        fields = [
            "id", "name", "committee_type", "plants", "plant_codes", "description",
            "is_management_body", "members", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_plant_codes(self, obj):
        return sorted(p.code for p in obj.plants.all())

    def get_members(self, obj):
        from .services import sort_members
        # Tutte le cariche, anche chiuse: la composizione storica serve a chi
        # rilegge un verbale passato. L'interfaccia separa in carica/cessati.
        return CommitteeMemberSerializer(sort_members(obj.members.all()), many=True).data


class SecurityObjectiveMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityObjectiveMeasurement
        fields = ["id", "objective", "measured_on", "value", "note", "created_at"]
        read_only_fields = ["created_by", "created_at", "updated_at", "deleted_at"]


class SecurityObjectiveSerializer(serializers.ModelSerializer):
    # Dati strutturati, non etichette: le stringhe le compone il frontend nella
    # lingua dell'utente (lezione di RoleAssignmentSerializer.scope_code).
    plant_code = serializers.SerializerMethodField(read_only=True)
    kpi_code = serializers.SerializerMethodField(read_only=True)
    evaluation = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SecurityObjective
        fields = "__all__"
        # Il ciclo di vita passa dalle azioni dedicate (attiva, sospendi,
        # chiudi), che validano e scrivono l'audit: mai da una PATCH generica.
        read_only_fields = [
            "created_by", "created_at", "updated_at", "deleted_at",
            "status", "closed_at", "closed_by", "closure_note",
        ]
        # I vincoli di unicità su (code, plant) sono condizionali: il validator
        # DRF generato d'ufficio non conosce la condizione e rifiuterebbe una
        # PATCH che non tocca il codice (stesso inciampo di RoleAssignment).
        validators = []

    def get_plant_code(self, obj):
        return obj.plant.code if obj.plant_id else None

    def get_kpi_code(self, obj):
        return obj.kpi_definition.kpi_code if obj.kpi_definition_id else None

    def get_evaluation(self, obj):
        """Andamento calcolato. In lista i valori correnti arrivano già
        caricati in blocco dal ViewSet via context (`objective_values`), così
        la pagina resta a query costanti."""
        from .services import evaluate_objective

        cache = self.context.get("objective_values")
        if cache is None:
            return evaluate_objective(obj)
        # Se la cache c'è è autorevole: un obiettivo che non vi compare non ha
        # misure. Interrogarlo di nuovo rimetterebbe una query per riga.
        value, measured_on = cache.get(obj.id, (None, None))
        return evaluate_objective(obj, value=value, measured_on=measured_on)

    def validate_code(self, value):
        """Unicità del codice nel perimetro (sito, oppure organizzazione)."""
        qs = SecurityObjective.objects.filter(code=value)
        plant = self.initial_data.get("plant") or (
            str(self.instance.plant_id) if self.instance and self.instance.plant_id else None
        )
        qs = qs.filter(plant_id=plant) if plant else qs.filter(plant__isnull=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                _("Esiste già un obiettivo con questo codice in questo perimetro.")
            )
        return value
