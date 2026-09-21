from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from .models import (
    TrainingAudience,
    TrainingCourse,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)
from .permissions import TrainingPermission, TrainingRecordsPermission
from .serializers import (
    TrainingAudienceSerializer,
    TrainingCourseSerializer,
    TrainingPlanItemSerializer,
    TrainingPlanSerializer,
    TrainingSessionSerializer,
    control_option,
)
from . import services


class TrainingCourseViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.prefetch_related("plants", "controls__framework")
    serializer_class = TrainingCourseSerializer
    permission_classes = [TrainingPermission]
    filterset_fields = ["status", "mandatory", "source", "kind", "audience_kind"]
    search_fields = ["title", "description"]
    plant_field = "plants"
    allow_null_plant = True  # corso senza plants = catalogo globale
    audit_action = "training.course"

    def perform_destroy(self, instance):
        services.delete_course(instance, self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="training.course.create",
            level="L2",
            entity=instance,
            payload={"course_id": str(instance.pk)},
        )

    @action(detail=False, methods=["get"])
    def capabilities(self, request):
        """Cosa l'utente può leggere e dove può scrivere: leggibile da ogni
        ruolo, perché decide quali parti del modulo mostrare."""
        return Response(services.training_capabilities(request.user))

    @action(detail=False, methods=["get"], url_path="control-options")
    def control_options(self, request):
        """Controlli collegabili a un corso, cercati per codice (es. «A.6.3»).
        Serve a chi gestisce la formazione anche senza accesso al catalogo
        framework; solo codice, framework e titolo."""
        from apps.controls.models import Control

        qs = Control.objects.filter(framework__archived_at__isnull=True).select_related("framework")
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(external_id__icontains=search)
        lang = getattr(request, "LANGUAGE_CODE", "it")
        return Response([
            control_option(c, lang)
            for c in qs.order_by("framework__code", "external_id")[:50]
        ])


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
