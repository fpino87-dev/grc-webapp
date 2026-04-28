"""Views DRF modulo OSINT."""
from __future__ import annotations

import hashlib
import json
import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    AlertStatus,
    FindingStatus,
    OsintAlert,
    OsintEntity,
    OsintFinding,
    OsintScan,
    OsintSettings,
    OsintSubdomain,
    SubdomainStatus,
)
from core.jwt import ExportRateThrottle

from .permissions import OsintReadPermission, OsintWritePermission
from .serializers import (
    OsintAlertSerializer,
    OsintEntityDetailSerializer,
    OsintEntityListSerializer,
    OsintFindingSerializer,
    OsintScanDetailSerializer,
    OsintSettingsSerializer,
    OsintSubdomainSerializer,
)

logger = logging.getLogger(__name__)


class OsintEntityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [OsintReadPermission]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["entity_type", "is_active", "is_nis2_critical", "scan_frequency"]
    search_fields = ["domain", "display_name"]
    ordering_fields = ["display_name", "domain", "updated_at"]
    ordering = ["display_name"]

    def get_queryset(self):
        from django.db.models import Prefetch
        last_completed = (
            OsintScan.objects.filter(status="completed")
            .order_by("-scan_date")
        )
        # Solo gli ultimi 2 scan servono per last_scan + delta — taglia la N+1.
        # Il limit per-entità non è esprimibile in una sola query Postgres con Prefetch:
        # accettiamo `prefetch_related("scans")` con order, e gli adattatori prendono [:2].
        return (
            OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
            .prefetch_related(
                Prefetch("scans", queryset=last_completed, to_attr="_recent_completed_scans"),
            )
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

    @action(
        detail=False, methods=["get"], url_path="export",
        throttle_classes=[ExportRateThrottle],
    )
    def export_csv(self, request):
        """Export CSV evidence audit (entità + ultimo scan)."""
        import csv
        from io import StringIO
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow([
            "domain", "display_name", "entity_type", "is_nis2_critical",
            "scan_frequency", "last_scan_at", "last_score_total",
            "active_alerts_count",
        ])
        for e in self.get_queryset():
            w.writerow([
                e.domain, e.display_name, e.entity_type, e.is_nis2_critical,
                e.scan_frequency,
                e.last_scan_at.isoformat() if e.last_scan_at else "",
                e.last_score_total if e.last_score_total is not None else "",
                e.active_alerts_count_cached,
            ])
        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="osint_entities.csv"'
        return resp

    @action(detail=True, methods=["post"], permission_classes=[OsintWritePermission])
    def scan(self, request, pk=None):
        """Forza rescan immediato (asincrono). Lock per entità, TTL 5 min."""
        entity = self.get_object()
        from django.core.cache import cache
        lock_key = f"osint:scan_lock:{entity.pk}"
        if not cache.add(lock_key, "1", timeout=300):
            return Response(
                {"detail": "Scan già in corso per questa entità. Riprova fra qualche minuto."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.force_scan",
            level="L1",
            entity=entity,
            payload={"domain": entity.domain},
        )

        from apps.osint.tasks import run_entity_scan
        job = run_entity_scan.delay(str(entity.pk))
        return Response({"job_id": job.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)


class OsintAlertViewSet(viewsets.GenericViewSet):
    permission_classes = [OsintWritePermission]
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

        prev_status = alert.status
        alert.status = new_status
        if new_status == AlertStatus.RESOLVED:
            alert.resolved_at = timezone.now()
        alert.save(update_fields=["status", "resolved_at", "updated_at"])

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.alert_status_changed",
            level="L1",
            entity=alert,
            payload={
                "alert_type": alert.alert_type,
                "domain": alert.entity.domain,
                "from": prev_status,
                "to": new_status,
            },
        )
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

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.alert_escalated",
            level="L2",
            entity=alert,
            payload={
                "alert_type": alert.alert_type,
                "domain": alert.entity.domain,
                "decision": action_choice,
            },
        )
        return Response(self.get_serializer(alert).data)


class OsintSubdomainViewSet(viewsets.GenericViewSet):
    permission_classes = [OsintWritePermission]
    serializer_class = OsintSubdomainSerializer

    def get_queryset(self):
        return OsintSubdomain.objects.filter(deleted_at__isnull=True).select_related("entity")

    def list(self, request):
        status_filter = request.query_params.get("status")
        qs = self.get_queryset().order_by("status", "subdomain")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(self.get_serializer(qs, many=True).data)

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
        if new_status not in [SubdomainStatus.INCLUDED, SubdomainStatus.IGNORED, SubdomainStatus.PENDING]:
            return Response({"detail": "Stato non valido."}, status=status.HTTP_400_BAD_REQUEST)

        prev_status = sub.status
        sub.status = new_status
        sub.save(update_fields=["status", "updated_at"])

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.subdomain_classified",
            level="L1",
            entity=sub,
            payload={
                "subdomain": sub.subdomain,
                "from": prev_status,
                "to": new_status,
            },
        )
        return Response(self.get_serializer(sub).data)


class OsintDashboardView(viewsets.GenericViewSet):
    permission_classes = [OsintReadPermission]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        # Niente aggregator qui — viene chiamato da signal/POST sync esplicito.
        from django.db.models import Count, Q
        from apps.osint.scoring import classify_score

        entities = OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True)
        total = entities.count()

        # Score classification via campo denormalizzato.
        critical_count = 0
        warning_count = 0
        for score in entities.exclude(last_score_total__isnull=True).values_list("last_score_total", flat=True):
            cls = classify_score(score)
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

    @action(detail=False, methods=["post"], permission_classes=[OsintWritePermission])
    def sync(self, request):
        """Sincronizza esplicitamente le entità OSINT con i moduli sorgente."""
        from apps.osint.services import aggregate_entities
        result = aggregate_entities()

        from core.audit import log_action
        from apps.osint.models import OsintSettings
        log_action(
            user=request.user,
            action_code="osint.entities_synced",
            level="L1",
            entity=OsintSettings.load(),
            payload={
                "created": result.created,
                "updated": result.updated,
                "reactivated": result.reactivated,
                "deactivated": result.deactivated,
            },
        )
        return Response({
            "created": result.created,
            "updated": result.updated,
            "reactivated": result.reactivated,
            "deactivated": result.deactivated,
        })


class OsintSettingsViewSet(viewsets.GenericViewSet):
    permission_classes = [OsintWritePermission]
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

        # Logga senza esporre le API key (anche tronche).
        sensitive = {"hibp_api_key", "virustotal_api_key", "abuseipdb_api_key", "gsb_api_key", "otx_api_key"}
        changed_keys = [k for k in request.data.keys() if k not in sensitive]
        api_key_touched = any(k in sensitive for k in request.data.keys())

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.settings_updated",
            level="L2",
            entity=settings,
            payload={
                "fields_changed": sorted(changed_keys),
                "api_keys_touched": api_key_touched,
            },
        )
        return Response(serializer.data)


class OsintAiView(viewsets.GenericViewSet):
    permission_classes = [OsintWritePermission]

    @action(detail=False, methods=["post"])
    def analyze(self, request):
        """Chiama AI Engine con dati OSINT anonimizzati."""
        analysis_type = request.data.get("type")
        if analysis_type not in ("attack_surface", "suppliers_nis2", "board_report"):
            return Response({"detail": "type non valido."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.osint.anonymizer import AnonymizationService, OSINT_SYSTEM_PROMPT
        from apps.osint.scoring import classify_score
        from apps.ai_engine.router import route

        def _strip_unsafe(value: str, max_len: int = 80) -> str:
            """Rimuove caratteri di controllo e neutralizza i delimitatori di placeholder.

            Defense-in-depth contro prompt injection: anche con anonimizzazione
            attiva un nome utente-controllato non deve poter chiudere/aprire
            placeholder o iniettare istruzioni con caratteri di controllo.
            """
            if not isinstance(value, str):
                return value
            # Caratteri di controllo (incluso \n, \r, \t) eliminati.
            cleaned = "".join(ch for ch in value if ch.isprintable())
            cleaned = cleaned.replace("[", "(").replace("]", ")")
            return cleaned[:max_len].strip()

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
                "domain": _strip_unsafe(e.domain, max_len=255),
                "display_name": _strip_unsafe(e.display_name),
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


class OsintFindingViewSet(viewsets.GenericViewSet):
    """API per i finding persistenti (menù Risoluzione)."""
    permission_classes = [OsintWritePermission]
    serializer_class = OsintFindingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "severity", "code", "entity"]
    ordering_fields = ["last_seen", "severity", "first_seen"]
    ordering = ["-last_seen"]

    def get_queryset(self):
        return (
            OsintFinding.objects.filter(deleted_at__isnull=True)
            .select_related("entity", "scan")
        )

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        # Filtro speciale "open_only" — esclude resolved/accepted_risk per default UI.
        if request.query_params.get("open_only") in ("1", "true"):
            qs = qs.filter(status__in=[FindingStatus.OPEN, FindingStatus.ACKNOWLEDGED, FindingStatus.IN_PROGRESS])
        return Response(self.get_serializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        try:
            obj = self.get_queryset().get(pk=pk)
        except OsintFinding.DoesNotExist:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(obj).data)

    def partial_update(self, request, pk=None):
        try:
            finding = self.get_queryset().get(pk=pk)
        except OsintFinding.DoesNotExist:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status and new_status not in [c[0] for c in FindingStatus.choices]:
            return Response({"detail": "Stato non valido."}, status=status.HTTP_400_BAD_REQUEST)

        prev_status = finding.status
        if new_status:
            finding.status = new_status
            if new_status == FindingStatus.RESOLVED:
                finding.resolved_at = timezone.now()

        if "resolution_note" in request.data:
            note = (request.data.get("resolution_note") or "").strip()[:2000]
            finding.resolution_note = note

        if "accepted_risk_until" in request.data:
            finding.accepted_risk_until = request.data.get("accepted_risk_until") or None

        finding.save()

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.finding_updated",
            level="L1",
            entity=finding,
            payload={
                "code": finding.code,
                "domain": finding.entity.domain,
                "from": prev_status,
                "to": finding.status,
            },
        )
        return Response(self.get_serializer(finding).data)

    @action(detail=True, methods=["post"], url_path="create-task")
    def create_task(self, request, pk=None):
        """Genera un task M08 per la risoluzione del finding."""
        try:
            finding = self.get_queryset().get(pk=pk)
        except OsintFinding.DoesNotExist:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)

        from datetime import timedelta
        from apps.tasks.models import Task
        from apps.osint.findings import get_playbook
        playbook = get_playbook(finding.code) or {}
        title_short = playbook.get("title", finding.get_code_display())
        steps = playbook.get("fix_steps", [])
        steps_md = "\n".join(f"- {s}" for s in steps) if steps else ""
        task = Task.objects.create(
            title=f"OSINT: {title_short} — {finding.entity.display_name}",
            description=(
                f"[Generato dal modulo OSINT — Risoluzione]\n\n"
                f"Dominio: {finding.entity.domain}\n"
                f"Code: {finding.code}\n"
                f"Severità: {finding.severity}\n\n"
                f"## Cosa\n{playbook.get('what', '')}\n\n"
                f"## Impatto\n{playbook.get('impact', '')}\n\n"
                f"## Passi\n{steps_md}\n"
            ),
            priority="alta" if finding.severity == "critical" else "media",
            due_date=(timezone.now() + timedelta(days=14)).date(),
            source="manuale",
            source_module="osint",
            source_id=finding.pk,
            status="aperto",
        )
        finding.linked_task_id = task.pk
        if finding.status == FindingStatus.OPEN:
            finding.status = FindingStatus.IN_PROGRESS
        finding.save(update_fields=["linked_task_id", "status", "updated_at"])

        from core.audit import log_action
        log_action(
            user=request.user,
            action_code="osint.finding_task_created",
            level="L1",
            entity=finding,
            payload={"task_id": str(task.pk), "code": finding.code},
        )
        return Response({"task_id": str(task.pk), "finding": self.get_serializer(finding).data})

    @action(detail=False, methods=["post"], url_path="bulk-task")
    def bulk_task(self, request):
        """Genera un task per ogni finding nella lista."""
        ids = request.data.get("finding_ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "finding_ids vuoto o non valido."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for fid in ids[:100]:  # cap difensivo
            req = type("R", (), {"user": request.user, "data": {}})()
            resp = self.create_task(req, pk=fid)
            results.append({"finding_id": fid, "status_code": resp.status_code})
        return Response({"created": len([r for r in results if r["status_code"] == 200]), "results": results})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from django.db.models import Count
        qs = self.get_queryset().filter(
            status__in=[FindingStatus.OPEN, FindingStatus.ACKNOWLEDGED, FindingStatus.IN_PROGRESS],
        )
        by_severity = {row["severity"]: row["c"] for row in qs.values("severity").annotate(c=Count("id"))}
        by_code = list(
            qs.values("code", "severity").annotate(c=Count("id")).order_by("-c")
        )

        # Risolti negli ultimi 7 giorni
        from datetime import timedelta
        recent_resolved = OsintFinding.objects.filter(
            status=FindingStatus.RESOLVED,
            resolved_at__gte=timezone.now() - timedelta(days=7),
            deleted_at__isnull=True,
        ).count()

        return Response({
            "open_critical": by_severity.get("critical", 0),
            "open_warning": by_severity.get("warning", 0),
            "open_info": by_severity.get("info", 0),
            "resolved_last_7d": recent_resolved,
            "by_code": by_code,
        })

    @action(
        detail=False, methods=["get"], url_path="export",
        throttle_classes=[ExportRateThrottle],
    )
    def export_csv(self, request):
        """Export CSV per audit GRC."""
        import csv
        from io import StringIO
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow([
            "code", "severity", "status", "entity_domain", "entity_display_name",
            "is_nis2_critical", "first_seen", "last_seen", "resolved_at",
            "resolution_note", "linked_task_id",
        ])
        for f in self.get_queryset():
            w.writerow([
                f.code, f.severity, f.status, f.entity.domain, f.entity.display_name,
                f.entity.is_nis2_critical,
                f.first_seen.isoformat(), f.last_seen.isoformat(),
                f.resolved_at.isoformat() if f.resolved_at else "",
                (f.resolution_note or "").replace("\n", " "),
                str(f.linked_task_id) if f.linked_task_id else "",
            ])
        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="osint_findings.csv"'
        return resp
