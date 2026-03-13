from rest_framework import decorators, response, status, viewsets

from core.audit import log_action
from .models import Incident
from .serializers import IncidentSerializer
from .services import close_incident


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.select_related("plant", "closed_by").prefetch_related("assets")
    serializer_class = IncidentSerializer

    @decorators.action(detail=True, methods=["post"])
    def confirm_nis2(self, request, pk=None):
        incident = self.get_object()
        incident.nis2_notifiable = request.data.get("nis2_notifiable", "si")
        incident.save(update_fields=["nis2_notifiable"])
        log_action(
            user=request.user,
            action_code="incidents.confirm_nis2",
            level="L2",
            entity=incident,
            payload={"nis2_notifiable": incident.nis2_notifiable},
        )
        return response.Response(self.get_serializer(incident).data)

    @decorators.action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        incident = self.get_object()
        close_incident(incident, request.user)
        return response.Response(self.get_serializer(incident).data)

