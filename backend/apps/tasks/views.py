from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task, TaskComment
from .serializers import TaskCommentSerializer, TaskSerializer
from . import services


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related(
        "plant", "assigned_to", "completed_by", "escalated_to"
    ).prefetch_related("comments")
    serializer_class = TaskSerializer
    filterset_fields = ["plant", "status", "priority", "source", "assigned_to"]
    search_fields = ["title", "description"]

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
        tasks = services.get_overdue_tasks(plant_id=plant_id)
        return Response(TaskSerializer(tasks, many=True).data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    queryset = TaskComment.objects.select_related("task", "author")
    serializer_class = TaskCommentSerializer
    filterset_fields = ["task"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
