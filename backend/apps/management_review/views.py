from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from .models import ManagementReview, ReviewAction
from .serializers import ManagementReviewSerializer, ReviewActionSerializer
from . import services


class ManagementReviewViewSet(viewsets.ModelViewSet):
    queryset = ManagementReview.objects.all()
    serializer_class = ManagementReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="management_review.review.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        review = self.get_object()
        review = services.complete_review(review, request.user)
        serializer = self.get_serializer(review)
        return Response(serializer.data)


class ReviewActionViewSet(viewsets.ModelViewSet):
    queryset = ReviewAction.objects.all()
    serializer_class = ReviewActionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["review"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="management_review.action.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "review_id": str(instance.review_id)},
        )
