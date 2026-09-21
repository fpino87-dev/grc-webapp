from django.db.models import Prefetch
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from .models import (
    TrainingAudience,
    TrainingCourse,
    TrainingEvidenceControl,
    TrainingParticipant,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)
from .permissions import TrainingPermission, TrainingRecordsPermission
from .serializers import (
    TrainingAudienceSerializer,
    TrainingCourseSerializer,
    TrainingEvidenceControlSerializer,
    TrainingPlanItemSerializer,
    TrainingPlanSerializer,
    TrainingSessionSerializer,
    control_option,
)
from . import services


class TrainingCourseViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.prefetch_related("plants")
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
        services.create_course(serializer, self.request.user)

    def perform_update(self, serializer):
        services.update_course(serializer, self.request.user)

    @action(detail=False, methods=["get"])
    def capabilities(self, request):
        """Cosa l'utente può leggere e dove può scrivere: leggibile da ogni
        ruolo, perché decide quali parti del modulo mostrare."""
        return Response(services.training_capabilities(request.user))

    @action(detail=False, methods=["get"], url_path="competency-options")
    def competency_options(self, request):
        """Competenze richieste ai ruoli (ISO 27001 cl. 7.2), da proporre come
        competenza attribuita da un corso per ruoli critici o per il CdA."""
        return Response(services.competency_options())

    @action(detail=False, methods=["get"], url_path="control-options")
    def control_options(self, request):
        """Controlli da impostare come provati dalle erogazioni, cercati per
        codice (es. «PR.AT-01»).
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


class TrainingEvidenceControlViewSet(_ServiceWriteMixin, viewsets.ModelViewSet):
    """Quali controlli provano le erogazioni, per tipo di destinatari: vale per
    tutta l'organizzazione, la gestisce chi ha perimetro di organizzazione."""
    queryset = TrainingEvidenceControl.objects.select_related("control__framework")
    serializer_class = TrainingEvidenceControlSerializer
    permission_classes = [TrainingRecordsPermission]
    http_method_names = ["get", "post", "delete", "head", "options"]
    filterset_fields = ["audience_kind"]
    create_service = services.create_evidence_control
    delete_service = services.delete_evidence_control


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
    ).prefetch_related(
        "audiences",
        Prefetch(
            "participants",
            queryset=TrainingParticipant.objects.select_related("user", "committee_member__committee"),
        ),
    )
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

    @action(detail=False, methods=["get"], url_path="participant-options")
    def participant_options(self, request):
        """Chi si può indicare come partecipante di un'erogazione nominativa del
        sito alla data indicata. Nomi di persone: solo a chi gestisce la
        formazione del sito."""
        from apps.plants.models import Plant

        plant = Plant.objects.filter(pk=request.query_params.get("plant")).first() \
            if _is_uuid(request.query_params.get("plant")) else None
        if plant is None:
            return Response({"plant": [_("Indica il sito.")]}, status=status.HTTP_400_BAD_REQUEST)
        services.require_training_manage(request.user, plant)
        day = parse_date(request.query_params.get("held_on") or "") or timezone.localdate()
        return Response(services.participant_options(plant, day))

    @action(detail=False, methods=["get"], url_path="board-status")
    def board_status(self, request):
        """Formazione dell'organo di gestione (NIS2 art. 20) del sito, o di tutti
        i siti per lo scope di organizzazione: chi è in carica e fino a quando
        la sua formazione è valida."""
        from apps.plants.models import Plant
        from core.scoping import require_plant_access

        raw = request.query_params.get("plant")
        plant = Plant.objects.filter(pk=raw).first() if _is_uuid(raw) else None
        if raw and plant is None:
            return Response({"plant": [_("Sito non trovato.")]}, status=status.HTTP_400_BAD_REQUEST)
        require_plant_access(request.user, plant)
        return Response(services.board_training(plant))

    def update(self, request, *args, **kwargs):
        if "file" in request.FILES:
            return Response(
                {"file": [_(
                    "Il file di prova non si sostituisce: elimina l'erogazione e registrala di nuovo."
                )]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True
