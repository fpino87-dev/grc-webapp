from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from .models import (
    PhishingSimulation,
    TrainingAudience,
    TrainingCourse,
    TrainingEnrollment,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)
from .permissions import TrainingPermission, TrainingRecordsPermission, TrainingResultsPermission
from .serializers import (
    PhishingSimulationSerializer,
    TrainingAudienceSerializer,
    TrainingCourseSerializer,
    TrainingEnrollmentSerializer,
    TrainingPlanItemSerializer,
    TrainingPlanSerializer,
    TrainingSessionSerializer,
)
from . import services


class TrainingCourseViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.prefetch_related("plants", "controls")
    serializer_class = TrainingCourseSerializer
    permission_classes = [TrainingPermission]
    filterset_fields = ["status", "mandatory", "source", "kind", "audience_kind"]
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
            payload={"course_id": str(instance.pk)},
        )

    @action(detail=True, methods=["get"])
    def completion_rate(self, request, pk=None):
        # get_object() passa dal queryset scoped: niente tassi di completamento
        # di corsi di altri siti via pk diretto (sweep 2026-06-12).
        course = self.get_object()
        rate = services.get_completion_rate(course.pk)
        return Response({"course_id": str(course.pk), "completion_rate": rate})


class TrainingEnrollmentViewSet(PlantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Vecchie iscrizioni per persona: in sola lettura, aggregate nelle sessioni
    storiche dalla migrazione training.0004 e rimosse in una release successiva."""

    queryset = TrainingEnrollment.objects.select_related("course", "user")
    serializer_class = TrainingEnrollmentSerializer
    permission_classes = [TrainingResultsPermission]
    filterset_fields = ["course", "user", "status", "passed"]
    plant_field = "course__plants"
    allow_null_plant = True  # iscrizioni a corsi globali (senza plants)
    search_fields = ["user__username", "course__title"]


class PhishingSimulationViewSet(PlantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Vecchi esiti di phishing per persona: in sola lettura (vedi sopra)."""

    queryset = PhishingSimulation.objects.select_related("user", "plant")
    serializer_class = PhishingSimulationSerializer
    permission_classes = [TrainingResultsPermission]
    filterset_fields = ["plant", "result", "user"]
    search_fields = ["user__username", "kb4_simulation_id"]
    plant_field = "plant"
    allow_null_plant = True  # simulazioni cross-plant (campagne aziendali) senza plant


class _ServiceWriteMixin:
    """Create/update/destroy delegati ai servizi (regola #2): i servizi
    verificano anche il perimetro di gestione del sito."""

    create_service = update_service = delete_service = None

    def perform_create(self, serializer):
        type(self).create_service(serializer, self.request.user)

    def perform_update(self, serializer):
        type(self).update_service(serializer, self.request.user)

    def perform_destroy(self, instance):
        type(self).delete_service(instance, self.request.user)


class TrainingAudienceViewSet(_ServiceWriteMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingAudience.objects.select_related("plant")
    serializer_class = TrainingAudienceSerializer
    permission_classes = [TrainingRecordsPermission]
    filterset_fields = ["plant"]
    search_fields = ["name"]
    create_service = services.create_audience
    update_service = services.update_audience
    delete_service = services.delete_audience


class TrainingPlanViewSet(_ServiceWriteMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingPlan.objects.select_related("plant", "document")
    serializer_class = TrainingPlanSerializer
    permission_classes = [TrainingRecordsPermission]
    filterset_fields = ["plant", "year"]
    allow_null_plant = True  # piano di organizzazione
    create_service = services.create_plan
    update_service = services.update_plan
    delete_service = services.delete_plan

    @action(detail=True, methods=["get"], url_path="status")
    def plan_status(self, request, pk=None):
        return Response(services.plan_status(self.get_object()))


class TrainingPlanItemViewSet(_ServiceWriteMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingPlanItem.objects.select_related("plan", "course").prefetch_related("audiences")
    serializer_class = TrainingPlanItemSerializer
    permission_classes = [TrainingRecordsPermission]
    filterset_fields = ["plan", "course"]
    plant_field = "plan__plant"
    allow_null_plant = True
    create_service = services.create_plan_item
    update_service = services.update_plan_item
    delete_service = services.delete_plan_item


class TrainingSessionViewSet(_ServiceWriteMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related(
        "course", "plant", "evidence", "plan_item",
    ).prefetch_related("audiences")
    serializer_class = TrainingSessionSerializer
    permission_classes = [TrainingRecordsPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["plant", "course", "plan_item", "legacy"]
    allow_null_plant = True  # sessioni storiche di corsi/campagne senza sito
    update_service = services.update_session
    delete_service = services.delete_session

    def perform_create(self, serializer):
        self._created = services.register_session(
            serializer, self.request.FILES.get("file"), self.request.user,
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Esito del collegamento ai controlli: quanti collegati e quali non
        # applicabili al sito (solo codici di controllo, nessun dato personale).
        response.data["control_links"] = self._created.control_links
        return response

    def update(self, request, *args, **kwargs):
        if "file" in request.FILES:
            return Response(
                {"file": [_(
                    "Il file di prova non si sostituisce: elimina l'erogazione e registrala di nuovo."
                )]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)
