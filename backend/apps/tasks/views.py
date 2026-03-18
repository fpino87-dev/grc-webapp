from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task, TaskComment
from .serializers import TaskCommentSerializer, TaskSerializer
from . import services
from django.utils import timezone
from django.db.models import Q
from apps.auth_grc.models import UserPlantAccess
from apps.plants.models import Plant


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related(
        "plant", "assigned_to", "completed_by", "escalated_to"
    ).prefetch_related("comments")
    serializer_class = TaskSerializer
    filterset_fields = ["plant", "status", "priority", "source", "assigned_to"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if getattr(user, "is_superuser", False):
            return qs

        today = timezone.now().date()
        access_qs = (
            UserPlantAccess.objects.filter(
                user=user,
                deleted_at__isnull=True,
                valid_from__lte=today,
            )
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
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
