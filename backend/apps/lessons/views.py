from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import LessonLearned
from .serializers import LessonLearnedSerializer
from . import services


class LessonLearnedViewSet(viewsets.ModelViewSet):
    queryset = LessonLearned.objects.all()
    serializer_class = LessonLearnedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status", "category"]
    search_fields = ["title", "description"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="lessons.lesson_learned.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        lesson = self.get_object()
        lesson = services.validate_lesson(lesson, request.user)
        serializer = self.get_serializer(lesson)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def propagate(self, request, pk=None):
        lesson = self.get_object()
        plant_ids = request.data.get("plant_ids", [])
        lesson = services.propagate_to_plants(lesson, plant_ids, request.user)
        serializer = self.get_serializer(lesson)
        return Response(serializer.data)
