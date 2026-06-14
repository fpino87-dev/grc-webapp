from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from .models import PhishingSimulation, TrainingCourse, TrainingEnrollment
from .permissions import TrainingPermission, TrainingResultsPermission
from .serializers import (
    PhishingSimulationSerializer,
    TrainingCourseSerializer,
    TrainingEnrollmentSerializer,
)
from . import services


class TrainingCourseViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.prefetch_related("plants")
    serializer_class = TrainingCourseSerializer
    permission_classes = [TrainingPermission]
    filterset_fields = ["status", "mandatory", "source"]
    search_fields = ["title", "description"]
    plant_field = "plants"
    allow_null_plant = True  # corso senza plants = catalogo globale
    audit_action = "training.course"

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
        # get_object() passa dal queryset scoped: niente tassi di completamento
        # di corsi di altri siti via pk diretto (sweep 2026-06-12).
        course = self.get_object()
        rate = services.get_completion_rate(course.pk)
        return Response({"course_id": str(course.pk), "completion_rate": rate})


class TrainingEnrollmentViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingEnrollment.objects.select_related("course", "user")
    serializer_class = TrainingEnrollmentSerializer
    permission_classes = [TrainingResultsPermission]
    filterset_fields = ["course", "user", "status", "passed"]
    plant_field = "course__plants"
    allow_null_plant = True  # iscrizioni a corsi globali (senza plants)
    search_fields = ["user__username", "course__title"]
    audit_action = "training.enrollment"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="training.enrollment.create",
            level="L2",
            entity=instance,
            payload={"enrollment_id": str(instance.pk), "course_id": str(instance.course_id)},
        )


class PhishingSimulationViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PhishingSimulation.objects.select_related("user", "plant")
    serializer_class = PhishingSimulationSerializer
    permission_classes = [TrainingResultsPermission]
    filterset_fields = ["plant", "result", "user"]
    search_fields = ["user__username", "kb4_simulation_id"]
    plant_field = "plant"
    allow_null_plant = True  # simulazioni cross-plant (campagne aziendali) senza plant
    audit_action = "training.phishing"
