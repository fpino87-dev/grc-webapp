import hashlib
import json
from io import StringIO

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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


class AuditIntegrityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = AuditLog.objects.order_by("timestamp_utc")[:1000]
        checked = 0
        for log in logs:
            content = json.dumps(log.payload, sort_keys=True, default=str) + (log.prev_hash or "")
            expected = hashlib.sha256(content.encode()).hexdigest()
            if log.record_hash and expected != log.record_hash:
                return Response({
                    "status": "error",
                    "corrupted_id": str(log.id),
                    "action_code": log.action_code,
                    "message": f"Hash non corrispondente sul record {log.action_code}",
                })
            checked += 1
        return Response({
            "status": "ok",
            "checked": checked,
            "message": f"Integrità verificata — {checked} record controllati",
        })
