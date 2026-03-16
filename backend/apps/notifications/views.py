from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from . import services
from .models import EmailConfiguration, NotificationSubscription
from .serializers import (
    EmailConfigurationReadSerializer,
    EmailConfigurationSerializer,
    NotificationSubscriptionSerializer,
)


class NotificationSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NotificationSubscription.objects.select_related("user")
    serializer_class = NotificationSubscriptionSerializer
    filterset_fields = ["user", "event_type", "channel"]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    queryset = EmailConfiguration.objects.all()
    serializer_class = EmailConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        # Non esporre mai il campo password in GET
        if self.action in ("list", "retrieve"):
            return EmailConfigurationReadSerializer
        return EmailConfigurationSerializer

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        config = self.get_object()
        ok, error = services.test_email_connection(config)
        if ok:
            return Response(
                {
                    "ok": True,
                    "message": "Email di test inviata correttamente a " + config.username,
                }
            )
        return Response(
            {
                "ok": False,
                "error": error,
            },
            status=400,
        )

    @action(detail=False, methods=["get"], url_path="presets")
    def presets(self, request):
        return Response(EmailConfiguration.PROVIDER_PRESETS)
