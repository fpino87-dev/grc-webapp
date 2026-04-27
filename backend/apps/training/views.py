from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin

from .models import PhishingSimulation, TrainingCourse, TrainingEnrollment
from .serializers import (
    PhishingSimulationSerializer,
    TrainingCourseSerializer,
    TrainingEnrollmentSerializer,
)
from . import services


class TrainingCourseViewSet(viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.prefetch_related("plants")
    serializer_class = TrainingCourseSerializer
    filterset_fields = ["status", "mandatory", "source"]
    search_fields = ["title", "description"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="training.course.create",
            level="L2",
            entity=instance,
            payload={"course_id": str(instance.pk), "title": instance.title},
        )

    @action(detail=True, methods=["get"])
    def completion_rate(self, request, pk=None):
        rate = services.get_completion_rate(pk)
        return Response({"course_id": pk, "completion_rate": rate})


class TrainingEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = TrainingEnrollment.objects.select_related("course", "user")
    serializer_class = TrainingEnrollmentSerializer
    filterset_fields = ["course", "user", "status", "passed"]
    search_fields = ["user__username", "course__title"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="training.enrollment.create",
            level="L2",
            entity=instance,
            payload={"enrollment_id": str(instance.pk), "course_id": str(instance.course_id)},
        )


class PhishingSimulationViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PhishingSimulation.objects.select_related("user", "plant")
    serializer_class = PhishingSimulationSerializer
    filterset_fields = ["plant", "result", "user"]
    search_fields = ["user__username", "kb4_simulation_id"]
    plant_field = "plant"
    allow_null_plant = True  # simulazioni cross-plant (campagne aziendali) senza plant
