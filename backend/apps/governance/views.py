from rest_framework import viewsets

from core.audit import log_action
from .models import CommitteeMeeting, RoleAssignment, SecurityCommittee
from .serializers import (
    CommitteeMeetingSerializer,
    RoleAssignmentSerializer,
    SecurityCommitteeSerializer,
)


class RoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.all()
    serializer_class = RoleAssignmentSerializer

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="governance.role_assignment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )


class SecurityCommitteeViewSet(viewsets.ModelViewSet):
    queryset = SecurityCommittee.objects.all()
    serializer_class = SecurityCommitteeSerializer


class CommitteeMeetingViewSet(viewsets.ModelViewSet):
    queryset = CommitteeMeeting.objects.all()
    serializer_class = CommitteeMeetingSerializer

