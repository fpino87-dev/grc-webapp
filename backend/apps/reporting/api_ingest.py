"""
Endpoint machine-to-machine per il KPI engine operativo.

- KpiIngestView   POST /api/v1/kpi-ingest/   — ingestione KPI da script esterni
- KpiComputeView  POST /api/v1/kpi-compute/  — ricalcolo manuale snapshot KPI

L'ingest supporta due modalità di autenticazione:
  1) header `X-API-Key` confrontato con settings.KPI_INGEST_API_KEY;
  2) JWT di un utente `is_staff`.
Non usa SessionAuthentication, quindi nessun token CSRF è richiesto: gli
script esterni possono chiamare l'endpoint senza sessione browser.
"""
from django.conf import settings
from django.utils.crypto import constant_time_compare

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.tasks.serializers import _validate_kpi_code
from .permissions import ReportingPermission


class KpiIngestSerializer(serializers.Serializer):
    kpi_code = serializers.CharField(max_length=50)
    plant = serializers.UUIDField()
    value = serializers.FloatField()
    source = serializers.CharField(max_length=50)
    measured_at = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )

    def validate_kpi_code(self, value):
        return _validate_kpi_code(value)

    def validate_plant(self, value):
        from apps.plants.models import Plant

        if not Plant.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Plant inesistente.")
        return value


class KpiIngestView(APIView):
    """POST /api/v1/kpi-ingest/ — vedi docstring del modulo."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]  # autorizzazione gestita manualmente (dual-mode)

    def _authorized(self, request):
        configured = getattr(settings, "KPI_INGEST_API_KEY", "") or ""
        provided = request.headers.get("X-API-Key", "")
        via_api_key = bool(configured) and bool(provided) and constant_time_compare(
            provided, configured
        )
        user = request.user
        via_jwt_staff = bool(
            getattr(user, "is_authenticated", False) and user.is_staff
        )
        return via_api_key or via_jwt_staff

    def post(self, request):
        if not self._authorized(request):
            return Response(
                {"error": "Autenticazione richiesta: header X-API-Key valido "
                          "oppure JWT di utente staff."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = KpiIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )
        data = serializer.validated_data

        from apps.tasks import services

        user = request.user if getattr(request.user, "is_authenticated", False) else None
        snapshot = services.ingest_kpi_from_api(
            kpi_code=data["kpi_code"],
            plant_id=str(data["plant"]),
            value=data["value"],
            source=data["source"],
            measured_at=data.get("measured_at"),
            note=data.get("note", ""),
            user=user,
        )
        return Response(
            {
                "id": str(snapshot.id),
                "kpi_code": data["kpi_code"],
                "status": snapshot.status,
            },
            status=status.HTTP_201_CREATED,
        )


class KpiComputeView(APIView):
    """POST /api/v1/kpi-compute/ — ricalcolo manuale ('Calcola ora').
    Esegue il task in modalità eager e restituisce il riepilogo."""

    permission_classes = [ReportingPermission]

    def post(self, request):
        from apps.tasks.tasks import compute_operational_kpis

        result = compute_operational_kpis.apply()
        return Response({"detail": result.result}, status=status.HTTP_200_OK)
