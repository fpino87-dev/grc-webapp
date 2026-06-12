from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from django.core.exceptions import ValidationError

from .models import (
    ChecklistRun,
    ChecklistTemplate,
    KPIDefinition,
    OperationalKpiSnapshot,
    Task,
    TaskComment,
)
from .serializers import (
    ChecklistRunSerializer,
    ChecklistTemplateSerializer,
    KPIDefinitionListSerializer,
    KPIDefinitionSerializer,
    OperationalKpiSnapshotSerializer,
    TaskCommentSerializer,
    TaskSerializer,
)
from . import services
from .permissions import KpiConfigPermission, TaskPermission
from core.scoping import PlantScopedQuerysetMixin, require_plant_access
from django.db.models import Q
from django.utils import timezone
from apps.auth_grc.models import UserPlantAccess
from apps.plants.models import Plant


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related(
        "plant", "assigned_to", "completed_by", "escalated_to"
    ).prefetch_related("comments")
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["plant", "status", "priority", "source", "assigned_to"]
    search_fields = ["title", "description"]

    def perform_destroy(self, instance):
        from core.audit import log_action
        log_action(
            user=self.request.user,
            action_code="task.deleted",
            level="L1",
            entity=instance,
            payload={"id": str(instance.pk), "title": instance.title},
        )
        instance.soft_delete()

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if getattr(user, "is_superuser", False):
            return qs

        access_qs = (
            UserPlantAccess.objects.filter(
                user=user,
                deleted_at__isnull=True,
            )
            .prefetch_related("scope_plants", "scope_bu")
        )
        if not access_qs.exists():
            return qs.none()

        user_roles = set(access_qs.values_list("role", flat=True))

        # Determine allowed plants from access scopes.
        has_org_scope = access_qs.filter(scope_type="org").exists()
        allowed_plants: set[str] | None = None
        if not has_org_scope:
            allowed_plants = set()
            for access in access_qs:
                if access.scope_type == "bu" and access.scope_bu_id:
                    ids = Plant.objects.filter(bu_id=access.scope_bu_id).values_list("id", flat=True)
                    allowed_plants.update(ids)
                elif access.scope_type in ("plant_list", "single_plant"):
                    ids = access.scope_plants.all().values_list("id", flat=True)
                    allowed_plants.update(ids)

        assigned_to_q = Q(assigned_to=user)
        assigned_role_q = Q(assigned_role__in=user_roles)

        if allowed_plants is None:
            # org-scope: no plant restriction
            return qs.filter(assigned_to_q | assigned_role_q).distinct()

        plant_q = Q(plant__isnull=True) | Q(plant_id__in=allowed_plants)
        return qs.filter(assigned_to_q | (assigned_role_q & plant_q)).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        services.complete_task(task, request.user, request.data.get("notes", ""))
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        task = self.get_object()
        services.escalate_task(task, request.user)
        return Response(TaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        plant_id = request.query_params.get("plant")
        qs = self.get_queryset().filter(
            status__in=["aperto", "in_corso"],
            due_date__lt=timezone.localdate(),
        )
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(TaskSerializer(qs, many=True).data)


class TaskCommentViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaskComment.objects.select_related("task", "author")
    serializer_class = TaskCommentSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["task"]
    plant_field = "task__plant"
    allow_null_plant = True  # commenti su task org-wide (plant=null)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ── Quick Checklist (M08) ────────────────────────────────────────────────────


class ChecklistTemplateViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        ChecklistTemplate.objects.select_related("plant")
        .prefetch_related("items")
    )
    serializer_class = ChecklistTemplateSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["plant", "is_active", "frequency"]
    allow_null_plant = True  # template globali (plant=null) validi per tutti i plant
    search_fields = ["name", "description"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        from core.audit import log_action
        log_action(
            user=self.request.user,
            action_code="checklist_template.deleted",
            level="L1",
            entity=instance,
            payload={"id": str(instance.pk), "name": instance.name},
        )
        instance.soft_delete()


class ChecklistRunViewSet(
    PlantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """I run sono generati automaticamente via Celery; qui solo lettura,
    aggiornamento e completamento item — niente create/destroy manuali."""

    queryset = (
        ChecklistRun.objects.select_related("template", "plant", "assigned_to")
        .prefetch_related("items", "items__template_item")
    )
    serializer_class = ChecklistRunSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["plant", "status", "template", "assigned_to"]

    @action(detail=True, methods=["post"], url_path="complete-item")
    def complete_item(self, request, pk=None):
        run = self.get_object()
        item_id = request.data.get("item_id")
        if not item_id:
            return Response(
                {"detail": "item_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run_item = services.complete_run_item(
            run,
            item_id=item_id,
            checked=request.data.get("checked", False),
            note=request.data.get("note", ""),
            user=request.user,
            value=request.data.get("value"),
            text_value=request.data.get("text_value"),
        )
        if run_item is None:
            return Response(
                {"detail": "Item non trovato in questo run."},
                status=status.HTTP_404_NOT_FOUND,
            )
        run.refresh_from_db()
        return Response(ChecklistRunSerializer(run).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        run = self.get_object()
        try:
            services.complete_run(run, request.user)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ChecklistRunSerializer(run).data)


# ── KPI Engine operativo (M08 ↔ M18) ─────────────────────────────────────────


class KPIDefinitionViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        KPIDefinition.objects.select_related("plant", "checklist_template")
        .prefetch_related("snapshots")
    )
    permission_classes = [KpiConfigPermission]
    filterset_fields = ["plant", "is_active", "source", "aggregation"]
    allow_null_plant = True  # KPI globali multi-plant (plant=null)
    search_fields = ["kpi_code", "name", "description"]

    def get_serializer_class(self):
        if self.action == "list":
            return KPIDefinitionListSerializer
        return KPIDefinitionSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        from core.audit import log_action
        log_action(
            user=self.request.user,
            action_code="kpi_definition.deleted",
            level="L1",
            entity=instance,
            payload={"id": str(instance.pk), "kpi_code": instance.kpi_code},
        )
        instance.soft_delete()


class OperationalKpiSnapshotViewSet(
    PlantScopedQuerysetMixin,
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = OperationalKpiSnapshot.objects.select_related(
        "kpi_definition", "plant"
    )
    serializer_class = OperationalKpiSnapshotSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["kpi_definition", "plant", "week_start", "status"]
    allow_null_plant = True  # snapshot di KPI globali (plant=null)

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        week_from = params.get("week_start_after")
        week_to = params.get("week_start_before")
        if week_from:
            qs = qs.filter(week_start__gte=week_from)
        if week_to:
            qs = qs.filter(week_start__lte=week_to)
        return qs

    @action(detail=False, methods=["get"])
    def trend(self, request):
        """GET /kpi-snapshots/trend/?kpi_code=X&plant=Y&weeks=12 — ultimi N
        snapshot ordinati per week_start ASC (per il grafico trend)."""
        kpi_code = request.query_params.get("kpi_code")
        plant_id = request.query_params.get("plant")
        try:
            weeks = int(request.query_params.get("weeks", 12))
        except (TypeError, ValueError):
            weeks = 12
        weeks = min(max(weeks, 1), 52)

        if not kpi_code:
            return Response(
                {"detail": "kpi_code obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Il trend è costruito dal manager raw (non da get_queryset scoped):
        # serve accesso al plant richiesto; senza plant si leggono solo gli
        # snapshot globali (plant=null), legittimi per tutti (sweep 2026-06-12).
        require_plant_access(request.user, plant_id or None, aggregate_requires_org=False)

        qs = OperationalKpiSnapshot.objects.filter(
            kpi_definition__kpi_code=kpi_code
        ).select_related("kpi_definition", "plant")
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        else:
            qs = qs.filter(plant__isnull=True)

        # Ultimi N per data desc, poi riordinati ASC per il grafico.
        latest = list(qs.order_by("-week_start")[:weeks])
        latest.reverse()

        kpi_def = (
            KPIDefinition.objects.filter(kpi_code=kpi_code).first()
        )
        return Response({
            "kpi_code": kpi_code,
            "name": kpi_def.name if kpi_def else kpi_code,
            "unit": kpi_def.unit if kpi_def else "",
            "threshold_warning": kpi_def.threshold_warning if kpi_def else None,
            "threshold_critical": kpi_def.threshold_critical if kpi_def else None,
            "threshold_direction": kpi_def.threshold_direction if kpi_def else "above",
            "results": OperationalKpiSnapshotSerializer(latest, many=True).data,
        })
