from rest_framework import serializers

from .models import CommitteeMeeting, RoleAssignment, SecurityCommittee


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = "__all__"


class SecurityCommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityCommittee
        fields = "__all__"


class CommitteeMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeMeeting
        fields = "__all__"

