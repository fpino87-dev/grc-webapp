from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators, response, viewsets
from rest_framework.permissions import IsAuthenticated

from core.audit import log_action
from .models import Incident, NIS2Configuration
from .nis2_services import (
    classify_significance as classify_significance_service,
    generate_nis2_document,
    get_classification_method,
    mark_notification_sent,
    set_nis2_deadlines,
    update_pdca_with_nis2_evidence,
)
from .serializers import IncidentSerializer, NIS2ConfigurationSerializer, NIS2NotificationSerializer
from .services import close_incident


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.select_related("plant", "closed_by").prefetch_related("assets", "nis2_notifications")
    serializer_class = IncidentSerializer

    def perform_destroy(self, instance):
        log_action(
            user=self.request.user,
            action_code="incident.deleted",
            level="L2",
            entity=instance,
            payload={"title": instance.title, "severity": instance.severity},
        )
        instance.soft_delete()

    @decorators.action(detail=True, methods=["post"])
    def confirm_nis2(self, request, pk=None):
        incident = self.get_object()
        new_value = request.data.get("nis2_notifiable", "si")
        incident.nis2_notifiable = new_value
        incident.save(update_fields=["nis2_notifiable", "updated_at"])

        if new_value == "si":
            from .nis2_services import set_nis2_deadlines
            set_nis2_deadlines(incident)

        log_action(
            user=request.user,
            action_code="incidents.confirm_nis2",
            level="L1",
            entity=incident,
            payload={"nis2_notifiable": new_value},
        )
        return response.Response(self.get_serializer(incident).data)

    @decorators.action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        incident = self.get_object()
        close_incident(incident, request.user)
        return response.Response(self.get_serializer(incident).data)

    @decorators.action(detail=True, methods=["post"], url_path="classify-significance")
    def classify_significance(self, request, pk=None):
        incident = self.get_object()
        override = request.data.get("override")
        reason = request.data.get("reason", "")

        if override is not None:
            if not reason and override != incident.is_significant:
                return response.Response({"error": "Motivazione obbligatoria per override"}, status=400)
            incident.significance_override = override
            incident.significance_override_reason = reason
            incident.save(
                update_fields=[
                    "significance_override",
                    "significance_override_reason",
                    "updated_at",
                ]
            )

        is_sig = classify_significance_service(incident)
        incident.is_significant = is_sig
        incident.nis2_notifiable = "si" if is_sig else "no"
        incident.save(update_fields=["is_significant", "nis2_notifiable", "updated_at"])
        if is_sig:
            set_nis2_deadlines(incident)

        log_action(
            user=request.user,
            action_code="incident.nis2.classified",
            level="L1",
            entity=incident,
            payload={"is_significant": is_sig, "override": override},
        )
        return response.Response(
            {
                "ok": True,
                "is_significant": is_sig,
                "nis2_timeline": incident.nis2_timeline_status,
            }
        )

    @decorators.action(detail=True, methods=["get"], url_path="generate-document")
    def generate_document(self, request, pk=None):
        incident = self.get_object()
        notification_type = request.query_params.get("type", "formal_notification")
        html = generate_nis2_document(incident, notification_type, request.user)
        filename = (
            f"NIS2_{notification_type.upper()}_{str(incident.pk)[:8].upper()}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M')}.html"
        )
        log_action(
            user=request.user,
            action_code="incident.nis2.document.generated",
            level="L1",
            entity=incident,
            payload={"type": notification_type},
        )
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    @decorators.action(detail=True, methods=["post"], url_path="mark-sent")
    def mark_sent(self, request, pk=None):
        incident = self.get_object()
        notification_type = request.data.get("notification_type", "formal_notification")
        protocol_ref = request.data.get("protocol_ref", "")
        authority_response = request.data.get("authority_response", "")
        notif = mark_notification_sent(
            incident,
            notification_type,
            request.user,
            protocol_ref,
            authority_response,
        )
        update_pdca_with_nis2_evidence(incident, notif)
        return response.Response({"ok": True, "notification_id": str(notif.pk), "sent_at": str(notif.sent_at)})

    @decorators.action(detail=True, methods=["get"], url_path="nis2-timeline")
    def nis2_timeline(self, request, pk=None):
        incident = self.get_object()
        return response.Response(incident.nis2_timeline_status)

    @decorators.action(detail=True, methods=["get"], url_path="nis2-notifications")
    def nis2_notifications_list(self, request, pk=None):
        incident = self.get_object()
        notifs = incident.nis2_notifications.all()
        return response.Response(NIS2NotificationSerializer(notifs, many=True).data)

    @decorators.action(detail=True, methods=["get"], url_path="classification-method")
    def classification_method(self, request, pk=None):
        incident = self.get_object()
        return response.Response(get_classification_method(incident))


class NIS2ConfigurationViewSet(viewsets.ModelViewSet):
    queryset = NIS2Configuration.objects.select_related("plant")
    serializer_class = NIS2ConfigurationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["plant"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="incident.nis2config.created",
            level="L2",
            entity=instance,
            payload={"plant": str(instance.plant_id)},
        )

