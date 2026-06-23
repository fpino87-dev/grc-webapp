from rest_framework import serializers

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    CommitteeMeeting,
    DocumentWorkflowPolicy,
    RoleAssignment,
    RoleRequirement,
    SecurityCommittee,
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

    def validate(self, attrs):
        # Titolare unico: blocca una seconda nomina attiva dello stesso ruolo
        # sullo stesso perimetro (il bug delle assegnazioni duplicate). Solo in
        # creazione; il cambio titolare passa da "Sostituisci".
        if self.instance is None:
            from .services import is_single_holder

            role = attrs.get("role")
            if role and is_single_holder(role):
                today = timezone.localdate()
                dup = RoleAssignment.objects.filter(
                    role=role,
                    scope_type=attrs.get("scope_type"),
                    scope_id=attrs.get("scope_id"),
                    deleted_at__isnull=True,
                ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).exists()
                if dup:
                    raise serializers.ValidationError({
                        "role": _(
                            "Questo ruolo ha già un titolare attivo per questo "
                            "perimetro. Usa Sostituisci per cambiare il titolare."
                        )
                    })
        return attrs

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


class SecurityCommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityCommittee
        fields = "__all__"


class CommitteeMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeMeeting
        fields = "__all__"
        
