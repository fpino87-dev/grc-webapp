from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators, response, viewsets
from rest_framework.permissions import IsAuthenticated

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from .models import Incident, NIS2Configuration
from apps.plants.models import Plant

from .nis2_services import (
    classify_significance as classify_significance_service,
    generate_nis2_document,
    get_classification_breakdown,
    get_classification_method,
    mark_notification_sent,
    update_pdca_with_nis2_evidence,
)
from .serializers import IncidentSerializer, NIS2ConfigurationSerializer, NIS2NotificationSerializer
from .services import close_incident


class IncidentViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
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

        if isinstance(override, str):
            normalized = override.strip().lower()
            if normalized in ("true", "1", "yes", "si"):
                override = True
            elif normalized in ("false", "0", "no"):
                override = False
            else:
                override = None

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

        breakdown = classify_significance_service(incident)
        incident.refresh_from_db()
        is_sig = breakdown["decision"]["is_significant"]

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

    @decorators.action(detail=True, methods=["get"], url_path="classification-breakdown")
    def classification_breakdown(self, request, pk=None):
        """
        GET — Breakdown completo dopo salvataggio.
        Ricalcolo senza doppio salvataggio sulla stessa richiesta.
        """
        incident = self.get_object()
        plant = incident.plant
        if not plant or plant.nis2_scope == "non_soggetto":
            return response.Response(
                {
                    "nis2_scope": plant.nis2_scope if plant else "non_soggetto",
                    "message": "Sito non soggetto a NIS2.",
                    "decision": {"is_significant": False, "nis2_notifiable": "no"},
                }
            )

        breakdown = get_classification_breakdown(incident)
        return response.Response(breakdown)

    @decorators.action(detail=False, methods=["post"], url_path="classification-preview")
    def classification_preview(self, request):
        """
        POST — Preview in tempo reale senza salvare.
        Body: subset di campi incidente (anche parziale).
        Richiede plant_id per leggere la config.
        """
        from .nis2_classification import run_full_classification

        plant_id = request.data.get("plant_id")
        if not plant_id:
            return response.Response({"error": "plant_id obbligatorio"}, status=400)

        plant = Plant.objects.filter(pk=plant_id).first()
        if not plant:
            return response.Response({"error": "Plant non trovato"}, status=404)

        nis2_scope = plant.nis2_scope

        if nis2_scope == "non_soggetto":
            return response.Response(
                {
                    "nis2_scope": "non_soggetto",
                    "message": "Sito non soggetto a NIS2.",
                    "decision": {"is_significant": False, "nis2_notifiable": "no"},
                }
            )

        config_obj = NIS2Configuration.objects.filter(plant=plant).first()

        def _float(v, default=None):
            if v is None or v == "":
                return default
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        def _int(v, default=None):
            if v is None or v == "":
                return default
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        config = {
            "threshold_hours": float(config_obj.threshold_hours) if config_obj else 4.0,
            "threshold_financial": float(config_obj.threshold_financial) if config_obj else 100_000,
            "threshold_users": int(config_obj.threshold_users) if config_obj else 100,
            "multiplier_medium": float(config_obj.multiplier_medium) if config_obj else 2.0,
            "multiplier_high": float(config_obj.multiplier_high) if config_obj else 3.0,
            "ptnr_threshold": int(config_obj.ptnr_threshold) if config_obj else 4,
            "recurrence_score_bonus": int(config_obj.recurrence_score_bonus) if config_obj else 2,
            "recurrence_window_days": int(config_obj.recurrence_window_days) if config_obj else 90,
        }

        incident_data = {
            "service_disruption_hours": _float(request.data.get("service_disruption_hours"), 0.0),
            "financial_impact_eur": _float(request.data.get("financial_impact_eur"), 0.0),
            "affected_users_count": _int(request.data.get("affected_users_count"), 0),
            "personal_data_involved": bool(request.data.get("personal_data_involved", False)),
            "cross_border_impact": bool(request.data.get("cross_border_impact", False)),
            "critical_infrastructure_impact": bool(request.data.get("critical_infrastructure_impact", False)),
            "incident_category": request.data.get("incident_category", "") or "",
            "severity": request.data.get("severity", "bassa") or "bassa",
        }

        is_recurrent = bool(
            request.data.get("is_recurrent_override", request.data.get("is_recurrent", False))
        )

        breakdown = run_full_classification(incident_data, config, nis2_scope, is_recurrent)
        return response.Response(breakdown)


class NIS2ConfigurationViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
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

