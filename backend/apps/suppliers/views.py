from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import Supplier, SupplierAssessment
from .serializers import SupplierAssessmentSerializer, SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["risk_level", "status"]
    search_fields = ["name", "vat_number"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="suppliers.supplier.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "name": instance.name},
        )


class SupplierAssessmentViewSet(viewsets.ModelViewSet):
    queryset = SupplierAssessment.objects.all()
    serializer_class = SupplierAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["supplier"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="suppliers.assessment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "supplier_id": str(instance.supplier_id)},
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        from .services import complete_assessment

        assessment = self.get_object()
        result = complete_assessment(
            assessment,
            request.user,
            score_overall=request.data.get("score_overall"),
            score_governance=request.data.get("score_governance"),
            score_security=request.data.get("score_security"),
            score_bcp=request.data.get("score_bcp"),
            findings=request.data.get("findings", ""),
        )
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import approve_assessment

        assessment = self.get_object()
        try:
            result = approve_assessment(
                assessment,
                request.user,
                notes=request.data.get("notes", ""),
            )
            return Response({"ok": True, "status": result.status})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import reject_assessment

        assessment = self.get_object()
        try:
            result = reject_assessment(
                assessment,
                request.user,
                notes=request.data.get("notes", ""),
            )
            return Response({"ok": True, "status": result.status})
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=400)
