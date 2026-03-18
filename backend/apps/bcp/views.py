from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from apps.bia.serializers import CriticalProcessSerializer
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

    @action(detail=False, methods=["get"], url_path="missing-plans")
    def missing_plans(self, request):
        """GET /api/v1/bcp/plans/missing-plans/?plant=<uuid>
        Restituisce processi critici (criticality >= 4) senza BCP plan attivo.
        """
        plant_id = request.query_params.get("plant")
        if not plant_id:
            return Response({"detail": "Parametro 'plant' obbligatorio."}, status=400)
        from apps.plants.models import Plant
        try:
            plant = Plant.objects.get(pk=plant_id)
        except Plant.DoesNotExist:
            return Response({"detail": "Plant non trovato."}, status=404)
        missing = services.check_missing_bcp_plans(plant)
        serializer = CriticalProcessSerializer(missing, many=True)
        return Response(serializer.data)

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
        test_type = request.data.get("test_type", "tabletop")
        objectives = request.data.get("objectives") or []
        rto_achieved = request.data.get("rto_achieved_hours")
        rpo_achieved = request.data.get("rpo_achieved_hours")
        participants_count = request.data.get("participants_count") or 0
        try:
            test, warnings = services.record_test(
                plan,
                result,
                request.user,
                notes=notes,
                test_type=test_type,
                objectives=objectives,
                rto_achieved=rto_achieved,
                rpo_achieved=rpo_achieved,
                participants_count=participants_count,
            )
        except Exception as e:
            from django.core.exceptions import ValidationError

            if isinstance(e, ValidationError):
                return Response({"detail": str(e.message)}, status=400)
            raise
        serializer = BcpTestSerializer(test)
        return Response({"test": serializer.data, "warnings": warnings})

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        services.delete_bcp_plan(plan, request.user)
        return Response(status=204)


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

    def create(self, request, *args, **kwargs):
        """
        Mantiene compatibilità con la UI:
        POST /bcp/tests/ con payload senza test_date (viene impostata dal service).
        """
        from django.core.exceptions import ValidationError
        plan_id = request.data.get("plan")
        if not plan_id:
            return Response({"detail": "Parametro 'plan' obbligatorio."}, status=400)

        try:
            plan = BcpPlan.objects.get(pk=plan_id)
        except BcpPlan.DoesNotExist:
            return Response({"detail": "Piano BCP non trovato."}, status=404)

        result = request.data.get("result", "")
        notes = request.data.get("notes", "")
        test_type = request.data.get("test_type", "tabletop")
        objectives = request.data.get("objectives") or []
        rto_achieved = request.data.get("rto_achieved_hours")
        rpo_achieved = request.data.get("rpo_achieved_hours")
        participants_count = request.data.get("participants_count") or 0

        try:
            test, warnings = services.record_test(
                plan,
                result,
                request.user,
                notes=notes,
                test_type=test_type,
                objectives=objectives,
                rto_achieved=rto_achieved,
                rpo_achieved=rpo_achieved,
                participants_count=participants_count,
            )
        except ValidationError as e:
            return Response({"detail": str(e.message)}, status=400)

        serializer = BcpTestSerializer(test)
        return Response({"test": serializer.data, "warnings": warnings}, status=201)

    def destroy(self, request, *args, **kwargs):
        test = self.get_object()
        from core.audit import log_action
        test.soft_delete()
        log_action(
            user=request.user,
            action_code="bcp.test.deleted",
            level="L2",
            entity=test,
            payload={"id": str(test.id), "plan_id": str(test.plan_id)},
        )
        return Response(status=204)
