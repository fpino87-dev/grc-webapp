from rest_framework import serializers

from .models import CommitteeMeeting, DocumentWorkflowPolicy, RoleAssignment, SecurityCommittee


class RoleAssignmentSerializer(serializers.ModelSerializer):
    user_email  = serializers.SerializerMethodField(read_only=True)
    user_name   = serializers.SerializerMethodField(read_only=True)
    is_active   = serializers.SerializerMethodField(read_only=True)
    scope_label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = RoleAssignment
        fields = "__all__"

    def get_user_email(self, obj):
        return obj.user.email if obj.user_id else None

    def get_user_name(self, obj):
        if not obj.user_id:
            return None
        return obj.user.get_full_name() or obj.user.email

    def get_is_active(self, obj):
        return obj.is_active

    def get_scope_label(self, obj):
        if obj.scope_type == "org":
            return "Globale"
        if obj.scope_type == "bu" and obj.scope_id:
            from apps.plants.models import BusinessUnit
            bu = BusinessUnit.objects.filter(pk=obj.scope_id).first()
            return f"BU: {bu.code} — {bu.name}" if bu else f"BU: {obj.scope_id}"
        if obj.scope_type == "plant" and obj.scope_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=obj.scope_id).first()
            return f"Sito: {plant.code} — {plant.name}" if plant else f"Sito: {obj.scope_id}"
        return obj.scope_type or "—"


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
        
