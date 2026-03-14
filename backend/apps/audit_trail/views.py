from io import StringIO

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import AuditLog

from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only — audit trail is append-only"""

    queryset = AuditLog.objects.order_by("-timestamp_utc")
    serializer_class = AuditLogSerializer
    filterset_fields = ["user_id", "action_code", "entity_type"]
    search_fields = ["action_code"]
    ordering_fields = ["timestamp_utc"]

    @action(detail=False, methods=["get"])
    def verify_integrity(self, request):
        from django.core.management import call_command

        out = StringIO()
        try:
            call_command("verify_audit_trail_integrity", stdout=out)
            return Response({"ok": True, "output": out.getvalue()})
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=500)
