from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import AuditPrep, EvidenceItem
from .serializers import AuditPrepSerializer, EvidenceItemSerializer
from . import services


class AuditPrepViewSet(viewsets.ModelViewSet):
    queryset = AuditPrep.objects.all()
    serializer_class = AuditPrepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status", "framework"]
    search_fields = ["title", "auditor_name"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.auditprep.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        audit_prep = self.get_object()
        score = services.calc_readiness_score(audit_prep)
        return Response({"id": str(audit_prep.id), "readiness_score": score})


class EvidenceItemViewSet(viewsets.ModelViewSet):
    queryset = EvidenceItem.objects.all()
    serializer_class = EvidenceItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["audit_prep", "status"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.evidence.create",
            level="L2",
            entity=instance,
            payload={
                "id": str(instance.id),
                "audit_prep_id": str(instance.audit_prep_id),
            },
        )
