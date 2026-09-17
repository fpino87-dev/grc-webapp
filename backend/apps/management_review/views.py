import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin, get_user_plant_ids

from . import services
from .models import ManagementReview, ReviewAction, ReviewAgendaItem
from .permissions import ManagementReviewPermission
from .serializers import ManagementReviewSerializer, ReviewActionSerializer, ReviewAgendaItemSerializer


def _drf_error(exc: DjangoValidationError) -> DRFValidationError:
    """Errore di dominio (services) → 400 con `{"error": ..., "code": ...}`."""
    body = {"error": exc.messages[0] if exc.messages else str(exc)}
    if getattr(exc, "code", None):
        body["code"] = exc.code
    params = getattr(exc, "params", None) or {}
    if "missing" in params:
        body["missing"] = params["missing"]
    return DRFValidationError(body)


def _action_queryset():
    return ReviewAction.objects.select_related("owner", "task", "pdca_cycle")


class ManagementReviewViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ManagementReview.objects.select_related(
        "plant", "chair", "approved_by"
    ).prefetch_related(
        "attendees",
        Prefetch("actions", queryset=_action_queryset()),
        Prefetch("agenda_items", queryset=ReviewAgendaItem.objects.all()),
    )
    serializer_class = ManagementReviewSerializer
    permission_classes = [ManagementReviewPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status"]
    search_fields = ["title"]
    plant_field = "plant"

    def perform_create(self, serializer):
        services.create_review(serializer, self.request.user)

    def perform_update(self, serializer):
        try:
            services.update_review(serializer, self.request.user)
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_code="management_review.review.delete",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )
        instance.soft_delete()

    def _respond(self, review):
        review = self.get_queryset().get(pk=review.pk)
        return Response(self.get_serializer(review).data)

    def _run(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        review = self._run(services.start_review, self.get_object(), request.user)
        return self._respond(review)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        review = self._run(services.complete_review, self.get_object(), request.user)
        return self._respond(review)

    @action(detail=True, methods=["post"], url_path="generate-snapshot")
    def generate_snapshot(self, request, pk=None):
        snapshot = self._run(services.generate_snapshot, self.get_object(), request.user)
        return Response(snapshot)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        review = self._run(
            services.approve_review, self.get_object(), request.user, request.data.get("note", "")
        )
        return self._respond(review)

    @action(detail=False, methods=["get"], url_path="suggested-chair")
    def suggested_chair(self, request):
        plant_id = request.query_params.get("plant") or None
        if plant_id:
            try:
                plant_id = uuid.UUID(plant_id)
            except ValueError:
                return Response({"error": "plant non valido"}, status=400)
        user = services.suggest_chair(plant_id)
        if not user:
            return Response({"id": None, "name": None})
        name = f"{user.first_name} {user.last_name}".strip() or user.email
        return Response({"id": user.pk, "name": name})

    # ── Sintesi executive (bozza IA → accettazione umana) ──

    @action(detail=True, methods=["post", "delete"], url_path="summary-draft")
    def summary_draft(self, request, pk=None):
        from apps.ai_engine.router import LlmUnavailable

        review = self.get_object()
        if request.method == "DELETE":
            review = self._run(services.discard_summary_draft, review, request.user)
            return self._respond(review)
        lang = (request.data.get("lang") or "it")[:2]
        try:
            self._run(services.draft_executive_summary, review, request.user, lang)
        except LlmUnavailable:
            return Response({"error": "ai_unavailable"}, status=503)
        except ValueError as e:
            # Nessuna configurazione IA attiva
            return Response({"error": str(e), "code": "ai_not_configured"}, status=400)
        return self._respond(review)

    @action(detail=True, methods=["post"])
    def summary(self, request, pk=None):
        review = self._run(
            services.accept_executive_summary, self.get_object(), request.data.get("text", ""), request.user
        )
        return self._respond(review)

    # ── Relazione ──

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        from .report import render_html, render_pdf

        review = self.get_object()
        fmt = request.query_params.get("fmt", "html")
        if fmt not in ("html", "pdf"):
            return Response({"error": "formato non supportato"}, status=400)
        try:
            if fmt == "pdf":
                content, content_type = render_pdf(review), "application/pdf"
            else:
                content, content_type = render_html(review), "text/html; charset=utf-8"
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        filename = f"riesame_{review.id}"
        if review.review_date:
            filename += f"_{review.review_date.strftime('%Y%m%d')}"
        filename += f".{fmt}"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        log_action(
            user=request.user,
            action_code="management_review.report_downloaded",
            level="L1",
            entity=review,
            payload={"review_id": str(review.pk), "format": fmt},
        )
        return response


class ReviewAgendaItemViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ReviewAgendaItem.objects.select_related("review")
    serializer_class = ReviewAgendaItemSerializer
    permission_classes = [ManagementReviewPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["review"]
    plant_field = "review__plant"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def perform_create(self, serializer):
        try:
            serializer.instance = services.add_agenda_item(
                serializer.validated_data["review"], serializer.validated_data.get("title", ""),
                self.request.user,
            )
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    def perform_update(self, serializer):
        try:
            services.update_agenda_item(serializer.instance, serializer.validated_data, self.request.user)
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    def perform_destroy(self, instance):
        try:
            services.delete_agenda_item(instance, self.request.user)
        except DjangoValidationError as e:
            raise _drf_error(e) from e


class ReviewActionViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = _action_queryset().select_related("review")
    serializer_class = ReviewActionSerializer
    permission_classes = [ManagementReviewPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["review", "agenda_item"]
    plant_field = "review__plant"

    def perform_create(self, serializer):
        data = serializer.validated_data
        options = {
            "create_task": data.pop("create_task", False),
            "task_role": data.pop("task_role", ""),
            "create_pdca": data.pop("create_pdca", False),
            "objective": data.pop("objective", None),
        }
        pdca_plant_id = data.pop("pdca_plant", None)
        pdca_plant = None
        if options["create_pdca"] and pdca_plant_id:
            from apps.plants.models import Plant

            allowed = get_user_plant_ids(self.request.user)
            if allowed is not None and pdca_plant_id not in set(allowed):
                raise PermissionDenied("Sito non accessibile")
            pdca_plant = Plant.objects.filter(pk=pdca_plant_id).first()
        try:
            services.create_review_action(serializer, self.request.user, pdca_plant=pdca_plant, **options)
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    def perform_update(self, serializer):
        try:
            services.update_review_action(serializer, self.request.user)
        except DjangoValidationError as e:
            raise _drf_error(e) from e

    def perform_destroy(self, instance):
        try:
            services.delete_review_action(instance, self.request.user)
        except DjangoValidationError as e:
            raise _drf_error(e) from e
