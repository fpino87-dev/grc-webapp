from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import BcpPlan, BcpTest
from .serializers import BcpPlanSerializer, BcpTestSerializer
from . import services


class BcpPlanViewSet(viewsets.ModelViewSet):
    queryset = BcpPlan.objects.all()
    serializer_class = BcpPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="bcp.plan.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        plan = self.get_object()
        plan = services.approve_plan(plan, request.user)
        serializer = self.get_serializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def record_test(self, request, pk=None):
        plan = self.get_object()
        result = request.data.get("result", "")
        notes = request.data.get("notes", "")
        test = services.record_test(plan, result, request.user, notes=notes)
        serializer = BcpTestSerializer(test)
        return Response(serializer.data)


class BcpTestViewSet(viewsets.ModelViewSet):
    queryset = BcpTest.objects.all()
    serializer_class = BcpTestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["plan"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="bcp.test.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "plan_id": str(instance.plan_id)},
        )
