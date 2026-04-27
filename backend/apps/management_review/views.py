from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from .models import ManagementReview, ReviewAction
from .serializers import ManagementReviewSerializer, ReviewActionSerializer
from . import services


class ManagementReviewViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ManagementReview.objects.all()
    serializer_class = ManagementReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status"]
    search_fields = ["title"]
    plant_field = "plant"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="management_review.review.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_code="management_review.review.delete",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        review = self.get_object()
        review = services.complete_review(review, request.user)
        serializer = self.get_serializer(review)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="generate-snapshot")
    def generate_snapshot(self, request, pk=None):
        review = self.get_object()
        snapshot = services.generate_snapshot(review, request.user)
        return Response(snapshot)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from django.core.exceptions import ValidationError
        review = self.get_object()
        note = request.data.get("note", "")
        try:
            review = services.approve_review(review, request.user, note)
            serializer = self.get_serializer(review)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({"error": e.message}, status=400)

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        from django.http import HttpResponse
        from .report_generator import generate_review_report
        review = self.get_object()
        try:
            html = generate_review_report(review)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        filename = f"riesame_{review.id}"
        if review.review_date:
            filename += f"_{review.review_date.strftime('%Y%m%d')}"
        filename += ".html"
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        log_action(
            user=request.user,
            action_code="management_review.report_downloaded",
            level="L1",
            entity=review,
            payload={"review_id": str(review.pk)},
        )
        return response


class ReviewActionViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ReviewAction.objects.all()
    serializer_class = ReviewActionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["review"]
    plant_field = "review__plant"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="management_review.action.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "review_id": str(instance.review_id)},
        )
