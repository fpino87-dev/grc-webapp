from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import Supplier, SupplierAssessment
from .serializers import SupplierSerializer, SupplierAssessmentSerializer


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
