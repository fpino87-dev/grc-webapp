from io import StringIO

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import AuditLog, compute_record_hash

from .permissions import AuditLogIntegrityPermission, AuditLogReadPermission
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only — audit trail is append-only.

    Visibile solo a SUPER_ADMIN / COMPLIANCE_OFFICER / INTERNAL_AUDITOR /
    EXTERNAL_AUDITOR (ISO 27001 A.12.4.2: log accessibili solo a personale di
    sicurezza autorizzato). La verifica integrità richiede ruoli ancora più
    ristretti.
    """

    queryset = AuditLog.objects.order_by("-timestamp_utc")
    serializer_class = AuditLogSerializer
    filterset_fields = ["user_id", "action_code", "entity_type"]
    search_fields = ["action_code"]
    ordering_fields = ["timestamp_utc"]
    permission_classes = [AuditLogReadPermission]

    def get_permissions(self):  # type: ignore[override]
        if self.action == "verify_integrity":
            return [AuditLogIntegrityPermission()]
        return super().get_permissions()

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
    permission_classes = [AuditLogIntegrityPermission]

    def get(self, request):
        logs = AuditLog.objects.order_by("timestamp_utc")[:1000]
        checked = 0
        for log in logs:
            expected = compute_record_hash(log)
            if log.record_hash and expected != log.record_hash:
                return Response({
                    "status": "error",
                    "corrupted_id": str(log.id),
                    "action_code": log.action_code,
                    "hash_version": log.hash_version,
                    "message": f"Hash non corrispondente sul record {log.action_code}",
                })
            checked += 1
        return Response({
            "status": "ok",
            "checked": checked,
            "message": f"Integrità verificata — {checked} record controllati",
        })
