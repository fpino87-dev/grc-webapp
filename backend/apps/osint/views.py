"""Views DRF modulo OSINT."""
from __future__ import annotations

import hashlib
import json
import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    AlertStatus,
    OsintAlert,
    OsintEntity,
    OsintScan,
    OsintSettings,
    OsintSubdomain,
    SubdomainStatus,
)
from .serializers import (
    OsintAlertSerializer,
    OsintEntityDetailSerializer,
    OsintEntityListSerializer,
    OsintScanDetailSerializer,
    OsintSettingsSerializer,
    OsintSubdomainSerializer,
)

logger = logging.getLogger(__name__)


class OsintEntityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["entity_type", "is_active", "is_nis2_critical", "scan_frequency"]
    search_fields = ["domain", "display_name"]
    ordering_fields = ["display_name", "domain", "updated_at"]
    ordering = ["display_name"]

    def get_queryset(self):
        return (
            OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
            .prefetch_related("scans", "alerts", "subdomains")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OsintEntityDetailSerializer
        return OsintEntityListSerializer

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Storico scan (max 52 settimane)."""
        entity = self.get_object()
        scans = (
            OsintScan.objects.filter(entity=entity, status="completed")
            .order_by("-scan_date")[:52]
        )
        data = [
            {
                "scan_id": str(s.pk),
                "scan_date": s.scan_date,
                "score_total": s.score_total,
                "score_ssl": s.score_ssl,
                "score_dns": s.score_dns,
                "score_reputation": s.score_reputation,
                "score_grc_context": s.score_grc_context,
                "has_alerts": s.alerts.filter(status__in=["new", "acknowledged"]).exists(),
            }
            for s in scans
        ]
        return Response(data)

    @action(detail=True, methods=["get"], url_path=r"scans/(?P<scan_pk>[^/.]+)")
    def scan_detail(self, request, pk=None, scan_pk=None):
        entity = self.get_object()
        try:
            scan = OsintScan.objects.get(pk=scan_pk, entity=entity)
        except OsintScan.DoesNotExist:
            return Response({"detail": "Scan non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OsintScanDetailSerializer(scan).data)

    @action(detail=True, methods=["post"])
    def scan(self, request, pk=None):
        """Forza rescan immediato (asincrono)."""
        entity = self.get_object()
        from apps.osint.tasks import run_entity_scan
        job = run_entity_scan.delay(str(entity.pk))
        return Response({"job_id": job.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)


class OsintAlertViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OsintAlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "severity", "alert_type"]
    ordering_fields = ["created_at", "severity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return OsintAlert.objects.filter(deleted_at__isnull=True).select_related("entity", "scan")

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        try:
            alert = self.get_queryset().get(pk=pk)
        except OsintAlert.DoesNotExist:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status not in [AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED]:
            return Response({"detail": "Stato non valido."}, status=status.HTTP_400_BAD_REQUEST)

        alert.status = new_status
        if new_status == AlertStatus.RESOLVED:
            alert.resolved_at = timezone.now()
        alert.save(update_fields=["status", "resolved_at", "updated_at"])
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """Per alert pending_escalation: scegli routing manuale."""
        try:
            alert = self.get_queryset().get(pk=pk, status=AlertStatus.PENDING_ESCALATION)
        except OsintAlert.DoesNotExist:
            return Response({"detail": "Alert pending escalation non trovato."}, status=status.HTTP_404_NOT_FOUND)

        action_choice = request.data.get("action")
        if action_choice not in ("incident", "task", "ignore"):
            return Response({"detail": "Azione non valida. Usa: incident, task, ignore."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.osint.alerts import _create_incident, _create_task
        if action_choice == "incident":
            _create_incident(alert, alert.entity)
            alert.status = AlertStatus.ACKNOWLEDGED
        elif action_choice == "task":
            _create_task(alert, alert.entity)
            alert.status = AlertStatus.ACKNOWLEDGED
        else:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = timezone.now()

        alert.save(update_fields=["status", "resolved_at", "linked_incident_id", "linked_task_id", "updated_at"])
        return Response(self.get_serializer(alert).data)


class OsintSubdomainViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OsintSubdomainSerializer

    def get_queryset(self):
        return OsintSubdomain.objects.filter(deleted_at__isnull=True).select_related("entity")

    @action(detail=False, methods=["get"])
    def pending(self, request):
        qs = self.get_queryset().filter(status=SubdomainStatus.PENDING).order_by("subdomain")
        return Response(self.get_serializer(qs, many=True).data)

    def partial_update(self, request, pk=None):
        try:
            sub = self.get_queryset().get(pk=pk)
        except OsintSubdomain.DoesNotExist:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status not in [SubdomainStatus.INCLUDED, SubdomainStatus.IGNORED]:
            return Response({"detail": "Stato non valido."}, status=status.HTTP_400_BAD_REQUEST)

        sub.status = new_status
        sub.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(sub).data)


class OsintDashboardView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from apps.osint.services import aggregate_entities
        aggregate_entities()  # aggiorna entità prima di mostrare summary

        entities = OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
        total = entities.count()

        critical_count = 0
        warning_count = 0
        from apps.osint.scoring import classify_score
        for e in entities.prefetch_related("scans"):
            last = e.scans.filter(status="completed").order_by("-scan_date").first()
            if last:
                cls = classify_score(last.score_total)
                if cls == "critical":
                    critical_count += 1
                elif cls == "warning":
                    warning_count += 1

        last_scan = (
            OsintScan.objects.filter(status="completed").order_by("-scan_date").values_list("scan_date", flat=True).first()
        )
        pending_subdomains = OsintSubdomain.objects.filter(status="pending", deleted_at__isnull=True).count()

        from django_celery_beat.models import PeriodicTask
        next_scan = None
        try:
            pt = PeriodicTask.objects.get(name="OSINT Weekly Scanner", enabled=True)
            next_scan = str(pt.last_run_at) if pt.last_run_at else None
        except Exception:
            pass

        return Response({
            "total_entities": total,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "last_scan_date": last_scan,
            "next_scan_date": next_scan,
            "pending_subdomains": pending_subdomains,
        })


class OsintSettingsViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OsintSettingsSerializer

    def _get_settings(self):
        return OsintSettings.load()

    @action(detail=False, methods=["get"])
    def retrieve_settings(self, request):
        return Response(self.get_serializer(self._get_settings()).data)

    @action(detail=False, methods=["patch"])
    def update_settings(self, request):
        settings = self._get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OsintAiView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def analyze(self, request):
        """Chiama AI Engine con dati OSINT anonimizzati."""
        analysis_type = request.data.get("type")
        if analysis_type not in ("attack_surface", "suppliers_nis2", "board_report"):
            return Response({"detail": "type non valido."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.osint.anonymizer import AnonymizationService, OSINT_SYSTEM_PROMPT
        from apps.osint.scoring import classify_score
        from apps.ai_engine.router import route

        task_type_map = {
            "attack_surface": "osint_attack_surface",
            "suppliers_nis2": "osint_suppliers_nis2",
            "board_report": "osint_board_report",
        }
        task_type = task_type_map[analysis_type]

        # Costruisce payload delle entità più rilevanti (max 20 critiche/warning)
        entities = (
            OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
            .prefetch_related("scans")
        )
        if analysis_type == "suppliers_nis2":
            entities = entities.filter(entity_type__in=["supplier"], is_nis2_critical=True)

        entity_data = []
        settings = OsintSettings.load()
        for e in entities:
            last = e.scans.filter(status="completed").order_by("-scan_date").first()
            if not last:
                continue
            cls = classify_score(last.score_total)
            if analysis_type != "board_report" and cls == "ok":
                continue
            entity_data.append({
                "entity_type": e.entity_type,
                "domain": e.domain,
                "display_name": e.display_name,
                "is_nis2_critical": e.is_nis2_critical,
                "score_total": last.score_total,
                "score_ssl": last.score_ssl,
                "score_dns": last.score_dns,
                "score_reputation": last.score_reputation,
                "score_grc_context": last.score_grc_context,
                "ssl_days_remaining": last.ssl_days_remaining,
                "dmarc_present": last.dmarc_present,
                "dmarc_policy": last.dmarc_policy,
                "in_blacklist": last.in_blacklist,
                "vt_malicious": last.vt_malicious,
                "scan_date": str(last.scan_date.date()),
            })

        entity_data = sorted(entity_data, key=lambda x: -x["score_total"])[:20]

        if not entity_data:
            return Response({"analysis": "Nessuna entità con dati di scan disponibili."})

        # Anonimizzazione
        svc = AnonymizationService()
        if settings.anonymization_enabled:
            entity_data = [svc.anonymize_entity_dict(d) for d in entity_data]

        prompt_payloads = {
            "attack_surface": (
                "Analizza la superficie di attacco esposta dall'organizzazione basandoti sui "
                "dati OSINT seguenti. Identifica i rischi principali, le aree critiche e "
                "fornisci raccomandazioni prioritizzate.\n\nDati entità monitorati:\n"
                + json.dumps(entity_data, ensure_ascii=False, default=str)
            ),
            "suppliers_nis2": (
                "Analizza il profilo di rischio dei fornitori NIS2-critici basandoti sui "
                "dati OSINT. Per ogni fornitore con vulnerabilità evidenti, indica l'impatto "
                "sulla catena di fornitura e le azioni raccomandate.\n\nFornitori:\n"
                + json.dumps(entity_data, ensure_ascii=False, default=str)
            ),
            "board_report": (
                "Prepara un report sintetico per il Board/Audit sulla postura di sicurezza "
                "esterna dell'organizzazione. Usa linguaggio non tecnico, evidenzia trend, "
                "rischi materiali e azioni già intraprese.\n\nDati complessivi:\n"
                + json.dumps(entity_data, ensure_ascii=False, default=str)
            ),
        }
        prompt = prompt_payloads[analysis_type]

        try:
            result = route(
                task_type=task_type,
                prompt=prompt,
                system=OSINT_SYSTEM_PROMPT,
                user=request.user,
                entity_id=None,
                module_source="OSINT",
                sanitize=False,  # già anonimizzato sopra
            )
            text = result.get("text", "")
            if settings.anonymization_enabled:
                text = svc.deanonymize(text)
            return Response({"analysis": text})
        except Exception as exc:
            logger.error("OSINT AI analyze failed: %s", exc)
            return Response({"detail": "Errore chiamata AI. Verifica configurazione AI Engine."}, status=status.HTTP_502_BAD_GATEWAY)
