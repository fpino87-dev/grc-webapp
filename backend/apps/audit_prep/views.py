from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import AuditPrep, AuditFinding, EvidenceItem
from .serializers import AuditFindingSerializer, AuditPrepSerializer, EvidenceItemSerializer
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


class AuditFindingViewSet(viewsets.ModelViewSet):
    queryset = AuditFinding.objects.select_related(
        "audit_prep__plant", "control_instance__control",
        "pdca_cycle", "closed_by", "lesson_learned",
    )
    serializer_class = AuditFindingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["audit_prep", "finding_type", "status", "audit_prep__plant"]
    search_fields = ["title", "description"]

    def perform_create(self, serializer):
        data = self.request.data
        # Resolve audit_date string to date object if needed
        from datetime import date
        audit_date_raw = data.get("audit_date")
        if isinstance(audit_date_raw, str):
            from dateutil import parser as dateparser
            try:
                audit_date = dateparser.parse(audit_date_raw).date()
            except Exception:
                audit_date = date.today()
        else:
            audit_date = audit_date_raw or date.today()

        finding = services.open_finding(
            audit_prep=serializer.validated_data["audit_prep"],
            finding_type=data.get("finding_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            audit_date=audit_date,
            user=self.request.user,
            control_instance=serializer.validated_data.get("control_instance"),
            auditor_name=data.get("auditor_name", ""),
        )
        # Attach the created instance so DRF can return it
        serializer.instance = finding

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .services import close_finding
        from apps.documents.models import Evidence
        from django.core.exceptions import ValidationError

        finding = self.get_object()
        notes = request.data.get("closure_notes", "")
        evidence_id = request.data.get("evidence_id")
        evidence = None
        if evidence_id:
            evidence = Evidence.objects.filter(pk=evidence_id).first()
        try:
            finding = close_finding(finding, request.user, notes, evidence)
            return Response({"ok": True, "status": finding.status})
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)
