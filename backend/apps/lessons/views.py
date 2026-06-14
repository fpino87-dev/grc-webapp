from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin
from .models import LessonLearned
from .permissions import LessonLearnedPermission
from .serializers import LessonLearnedSerializer
from . import services


class LessonLearnedViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LessonLearned.objects.select_related("plant").all()
    serializer_class = LessonLearnedSerializer
    permission_classes = [LessonLearnedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status", "category"]
    search_fields = ["title", "description"]
    plant_field = "plant"
    audit_action = "lessons.lesson_learned"

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user,
            identified_by=serializer.validated_data.get("identified_by") or self.request.user,
        )
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
