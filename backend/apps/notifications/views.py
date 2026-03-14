from rest_framework import viewsets

from .models import NotificationSubscription
from .serializers import NotificationSubscriptionSerializer


class NotificationSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NotificationSubscription.objects.select_related("user")
    serializer_class = NotificationSubscriptionSerializer
    filterset_fields = ["user", "event_type", "channel"]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)
