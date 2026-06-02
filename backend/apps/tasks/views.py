from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from django.core.exceptions import ValidationError

from .models import ChecklistRun, ChecklistTemplate, Task, TaskComment
from .serializers import (
    ChecklistRunSerializer,
    ChecklistTemplateSerializer,
    TaskCommentSerializer,
    TaskSerializer,
)
from . import services
from django.db.models import Q
from django.utils import timezone
from apps.auth_grc.models import UserPlantAccess
from apps.plants.models import Plant


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related(
        "plant", "assigned_to", "completed_by", "escalated_to"
    ).prefetch_related("comments")
    serializer_class = TaskSerializer
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
            due_date__lt=timezone.now().date(),
        )
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(TaskSerializer(qs, many=True).data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    queryset = TaskComment.objects.select_related("task", "author")
    serializer_class = TaskCommentSerializer
    filterset_fields = ["task"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ── Quick Checklist (M08) ────────────────────────────────────────────────────


class ChecklistTemplateViewSet(viewsets.ModelViewSet):
    queryset = (
        ChecklistTemplate.objects.select_related("plant")
        .prefetch_related("items")
    )
    serializer_class = ChecklistTemplateSerializer
    filterset_fields = ["plant", "is_active", "frequency"]
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
