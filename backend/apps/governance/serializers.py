from rest_framework import serializers

from .models import CommitteeMeeting, RoleAssignment, SecurityCommittee


class RoleAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField(read_only=True)
    user_name  = serializers.SerializerMethodField(read_only=True)
    is_active  = serializers.SerializerMethodField(read_only=True)

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


class SecurityCommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityCommittee
        fields = "__all__"


class CommitteeMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeMeeting
        fields = "__all__"

