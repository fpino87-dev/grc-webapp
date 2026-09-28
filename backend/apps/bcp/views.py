import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.bia.serializers import CriticalProcessSerializer
from core.scoping import PlantScopedQuerysetMixin, get_user_plant_ids, require_plant_access
from . import services
from .models import BcpPlan, BcpTest
from .permissions import BcpPermission
from .serializers import BcpPlanSerializer, BcpTestSerializer


def _error(exc: ValidationError) -> Response:
    return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


def _json_list(value) -> list:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return value if isinstance(value, list) else []


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _record_test_from_request(plan, request) -> Response:
    data = request.data
    raw_date = data.get("test_date")
    test_date = parse_date(raw_date) if raw_date else None
    if raw_date and test_date is None:
        return Response({"detail": "Data del test non valida."}, status=400)
    try:
        test, warnings = services.record_test(
            plan,
            data.get("result", ""),
            request.user,
            notes=data.get("notes", ""),
            test_type=data.get("test_type", "tabletop"),
            objectives=_json_list(data.get("objectives")),
            rto_achieved=_to_int(data.get("rto_achieved_hours")),
            rpo_achieved=_to_int(data.get("rpo_achieved_hours")),
            participants_count=_to_int(data.get("participants_count")) or 0,
            evidence_ids=_json_list(data.get("evidence_ids")),
            evidence_file=request.FILES.get("evidence_file"),
            test_date=test_date,
        )
    except ValidationError as exc:
        return _error(exc)
    return Response(
        {"test": BcpTestSerializer(test).data, "warnings": warnings},
        status=status.HTTP_201_CREATED,
    )


class BcpPlanViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BcpPlan.objects.select_related("plant", "document", "critical_process").prefetch_related(
        "critical_processes",
        Prefetch("tests", queryset=BcpTest.objects.filter(deleted_at__isnull=True)),
    )
    serializer_class = BcpPlanSerializer
    permission_classes = [BcpPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status"]
    search_fields = ["title"]
    plant_field = "plant"

    def _process_ids(self):
        if "critical_processes" not in self.request.data:
            return None
        return _json_list(self.request.data.get("critical_processes"))

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except ValidationError as exc:
            return _error(exc)

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().update(request, *args, **kwargs)
        except ValidationError as exc:
            return _error(exc)

    def perform_create(self, serializer):
        plan = serializer.save(created_by=self.request.user)
        services.save_plan(plan, self.request.user, created=True, process_ids=self._process_ids())

    def perform_update(self, serializer):
        plan = serializer.save()
        data = self.request.data
        services.save_plan(
            plan, self.request.user, created=False, process_ids=self._process_ids(),
            frequency_changed="test_frequency_value" in data or "test_frequency_unit" in data,
        )

    def destroy(self, request, *args, **kwargs):
        services.delete_bcp_plan(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="missing-plans")
    def missing_plans(self, request):
        """Processi critici (criticità ≥ 4) del sito senza piano BCP approvato."""
        plant_id = request.query_params.get("plant")
        if not plant_id:
            return Response({"detail": "Parametro 'plant' obbligatorio."}, status=400)
        from apps.plants.models import Plant

        plant = Plant.objects.filter(pk=plant_id).first()
        if plant is None:
            return Response({"detail": "Plant non trovato."}, status=404)
        require_plant_access(request.user, plant)
        missing = services.check_missing_bcp_plans(plant)
        return Response(CriticalProcessSerializer(missing, many=True).data)

    @action(detail=False, methods=["get"])
    def coverage(self, request):
        """Processi critici con stato di copertura: coperto, scoperto per test
        scaduto, senza piano. `?plant=` facoltativo; senza, il perimetro
        dell'utente."""
        from apps.bia.models import CriticalProcess

        processes = CriticalProcess.objects.all()
        plant_id = request.query_params.get("plant")
        if plant_id:
            require_plant_access(request.user, plant_id)
            processes = processes.filter(plant_id=plant_id)
        else:
            allowed = get_user_plant_ids(request.user)
            if allowed is not None:
                processes = processes.filter(plant_id__in=allowed)
        return Response(services.coverage_rows(processes))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        plan = self.get_object()
        if not services.can_approve_plan(request.user, plan):
            return Response(
                {"detail": "Non hai i permessi per approvare questo piano BCP."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            plan = services.approve_plan(plan, request.user)
        except ValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(self.get_queryset().get(pk=plan.pk)).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        try:
            plan = services.archive_plan(self.get_object(), request.user)
        except ValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(self.get_queryset().get(pk=plan.pk)).data)

    @action(detail=True, methods=["post"])
    def record_test(self, request, pk=None):
        return _record_test_from_request(self.get_object(), request)


class BcpTestViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Storico dei test. Si registrano con POST (record_test) e si eliminano;
    non si modificano: esito e tempi sono evidenza di audit."""

    queryset = BcpTest.objects.select_related("plan", "plan__plant").prefetch_related("evidences")
    serializer_class = BcpTestSerializer
    permission_classes = [BcpPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"plan": ["exact"], "plan__plant": ["exact"]}
    plant_field = "plan__plant"
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        plan_id = request.data.get("plan")
        if not plan_id:
            return Response({"detail": "Parametro 'plan' obbligatorio."}, status=400)
        # Solo piani del perimetro dell'utente.
        plan = BcpPlan.objects.filter(pk=plan_id)
        allowed = get_user_plant_ids(request.user)
        if allowed is not None:
            plan = plan.filter(plant_id__in=allowed)
        plan = plan.select_related("plant").first()
        if plan is None:
            return Response({"detail": "Piano BCP non trovato."}, status=404)
        return _record_test_from_request(plan, request)

    def destroy(self, request, *args, **kwargs):
        services.delete_test(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def evidences(self, request, pk=None):
        """Aggiunge evidenze al test: file caricato e/o evidenze esistenti."""
        test = self.get_object()
        try:
            services.add_test_evidences(
                test,
                request.user,
                evidence_ids=_json_list(request.data.get("evidence_ids")),
                evidence_file=request.FILES.get("evidence_file"),
            )
        except ValidationError as exc:
            return _error(exc)
        return Response(BcpTestSerializer(self.get_queryset().get(pk=test.pk)).data)
