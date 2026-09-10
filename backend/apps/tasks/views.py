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
from .permissions import (
    ChecklistRunDeletePermission,
    KpiConfigPermission,
    TaskPermission,
)
from core.scoping import (
    PlantPayloadWriteGuardMixin,
    PlantScopedQuerysetMixin,
    require_plant_access,
)
from core.viewsets import SoftDeleteAuditMixin
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from apps.auth_grc.models import UserPlantAccess
from apps.plants.models import Plant


class TaskViewSet(PlantPayloadWriteGuardMixin, viewsets.ModelViewSet):
    # Scoping di lettura custom in get_queryset (ruoli + assegnatario); il
    # guard sulle scritture impedisce di creare/spostare task su un plant
    # fuori perimetro (sweep 2026-06-12 fase 2).
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


class TaskCommentViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaskComment.objects.select_related("task", "author")
    serializer_class = TaskCommentSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["task"]
    plant_field = "task__plant"
    allow_null_plant = True  # commenti su task org-wide (plant=null)
    audit_action = "tasks.task_comment"

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

    @action(detail=True, methods=["post"], url_path="start-run")
    def start_run(self, request, pk=None):
        """Avvia subito una checklist da questo template: unica via per i
        template ad hoc, che non sono schedulati, e riesecuzione fuori ciclo
        per gli altri. Scadenza di default: fine del periodo corrente."""
        template = self.get_object()

        if template.plant_id:
            plant = template.plant
        else:
            # Template globale: il sito va indicato esplicitamente.
            plant_id = request.data.get("plant")
            if not plant_id:
                return Response(
                    {"plant": _("Indicare il sito per cui avviare la checklist.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            plant = Plant.objects.filter(pk=plant_id, status="attivo").first()
            if plant is None:
                return Response(
                    {"plant": _("Sito non trovato o non attivo.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        require_plant_access(request.user, plant)

        due_date = request.data.get("due_date") or None
        if due_date is not None:
            due_date = parse_date(str(due_date))
            if due_date is None:
                return Response(
                    {"due_date": _("Data non valida (formato atteso AAAA-MM-GG).")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        run = services.start_manual_run(
            template, plant, due_date=due_date, user=request.user
        )
        return Response(
            ChecklistRunSerializer(run).data, status=status.HTTP_201_CREATED
        )


class ChecklistRunViewSet(
    PlantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """I run sono generati automaticamente via Celery (o avviati da un
    template con start-run); qui lettura, aggiornamento, completamento item e
    cancellazione motivata dei run non conclusi."""

    queryset = (
        ChecklistRun.objects.select_related("template", "plant", "assigned_to")
        .prefetch_related("items", "items__template_item")
    )
    serializer_class = ChecklistRunSerializer
    permission_classes = [TaskPermission]
    filterset_fields = ["plant", "status", "template", "assigned_to"]

    def get_permissions(self):
        if self.action == "destroy":
            return [ChecklistRunDeletePermission()]
        return super().get_permissions()

    def destroy(self, request, pk=None):
        run = self.get_object()
        try:
            services.delete_run(run, request.user, request.data.get("reason"))
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0] if exc.messages else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

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

    @action(detail=True, methods=["post"], url_path="record-value")
    def record_value(self, request, pk=None):
        """Inserimento manuale del valore, per i KPI che dipendono da una
        fonte esterna non ancora integrata."""
        from django.utils.dateparse import parse_date

        kpi = self.get_object()
        if kpi.source in ("checklist", "internal"):
            return Response(
                {"error": _("Questo KPI si calcola da solo: il valore non va inserito a mano.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw = request.data.get("value")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return Response(
                {"error": _("Valore numerico obbligatorio.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plant = kpi.plant
        plant_id = request.data.get("plant")
        if plant is None and plant_id:
            plant = Plant.objects.filter(pk=plant_id).first()
            if plant is None:
                return Response(
                    {"error": _("Sito non trovato.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        require_plant_access(request.user, plant, aggregate_requires_org=False)

        week_start = request.data.get("week_start")
        if week_start:
            week_start = parse_date(str(week_start))
            if week_start is None:
                return Response(
                    {"error": _("Settimana non valida (formato atteso AAAA-MM-GG).")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            week_start = services._monday_of(week_start)

        snapshot = services.record_manual_kpi_value(
            kpi, plant, value,
            week_start=week_start,
            note=request.data.get("note", ""),
            user=request.user,
        )
        return Response(
            OperationalKpiSnapshotSerializer(snapshot).data,
            status=status.HTTP_201_CREATED,
        )


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

        # Soglie e nome vengono dalla definizione del sito richiesto; se il
        # sito non ne ha una propria si ricade su quella globale.
        from apps.plants.models import Plant

        from . import services as tasks_services

        trend_plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        kpi_def = tasks_services.resolve_kpi_definition(kpi_code, trend_plant)
        return Response({
            "kpi_code": kpi_code,
            "name": kpi_def.name if kpi_def else kpi_code,
            "unit": kpi_def.unit if kpi_def else "",
            "threshold_warning": kpi_def.threshold_warning if kpi_def else None,
            "threshold_critical": kpi_def.threshold_critical if kpi_def else None,
            "threshold_direction": kpi_def.threshold_direction if kpi_def else "above",
            "results": OperationalKpiSnapshotSerializer(latest, many=True).data,
        })
