from django.utils import timezone
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.audit import log_action
from . import services
from .models import AuditFinding, AuditPrep, AuditProgram, EvidenceItem
from .serializers import (
    AuditFindingSerializer,
    AuditPrepSerializer,
    AuditProgramSerializer,
    EvidenceItemSerializer,
)


class AuditPrepViewSet(viewsets.ModelViewSet):
    queryset = AuditPrep.objects.all()
    serializer_class = AuditPrepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "status", "framework"]
    search_fields = ["title", "auditor_name"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.auditprep.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "title": instance.title},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.audit_program_id:
            from .services import sync_program_completion
            try:
                sync_program_completion(instance.audit_program)
            except Exception:
                pass
        log_action(
            user=self.request.user,
            action_code="audit_prep.updated",
            level="L2",
            entity=instance,
            payload={"status": instance.status},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        open_findings = instance.findings.filter(
            status__in=["open", "in_response"]
        ).count()
        if open_findings > 0:
            return Response(
                {
                    "error": (
                        f"Impossibile cancellare: ci sono {open_findings} finding aperti. "
                        f"Chiudi o archivia i finding prima di procedere."
                    )
                },
                status=400,
            )
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.deleted",
            level="L2",
            entity=instance,
            payload={
                "title": instance.title,
                "reason": request.data.get("reason", ""),
            },
        )
        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="annulla")
    def annulla(self, request, pk=None):
        """Annulla un AuditPrep avviato per errore."""
        instance = self.get_object()
        reason = request.data.get("reason", "")
        if not reason or len(reason.strip()) < 10:
            return Response(
                {
                    "error": "Motivo annullamento obbligatorio (min 10 caratteri)"
                },
                status=400,
            )
        instance.findings.filter(
            status__in=["open", "in_response"]
        ).update(status="closed")
        instance.status = "archiviato"
        instance.save(update_fields=["status", "updated_at"])
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.cancelled",
            level="L2",
            entity=instance,
            payload={"title": instance.title, "reason": reason},
        )
        return Response({"ok": True, "status": "archiviato"})

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        audit_prep = self.get_object()
        score = services.calc_readiness_score(audit_prep)
        return Response({"id": str(audit_prep.id), "readiness_score": score})

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Marca un AuditPrep come completato."""
        prep = self.get_object()
        open_majors = prep.findings.filter(
            finding_type="major_nc", status__in=["open", "in_response"]
        ).count()
        if open_majors > 0:
            return Response(
                {"error": f"Non puoi completare con {open_majors} Major NC aperti."},
                status=400,
            )
        prep.status = "completato"
        prep.save(update_fields=["status", "updated_at"])
        log_action(
            user=request.user,
            action_code="audit_prep.auditprep.completed",
            level="L1", entity=prep,
            payload={"title": prep.title},
        )
        return Response({"ok": True, "status": "completato"})

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        """Scarica relazione HTML dell'AuditPrep."""
        from .services import generate_audit_report
        from django.http import HttpResponse
        prep = self.get_object()
        html = generate_audit_report(prep)
        filename = (
            f"AuditReport_{prep.audit_date or 'draft'}_"
            f"{timezone.now().strftime('%Y%m%d')}.html"
        )
        log_action(
            user=request.user,
            action_code="audit_prep.report_downloaded",
            level="L2", entity=prep,
            payload={"filename": filename},
        )
        from django.http import HttpResponse
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class EvidenceItemViewSet(viewsets.ModelViewSet):
    queryset = EvidenceItem.objects.all()
    serializer_class = EvidenceItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["audit_prep", "status"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.evidence.create",
            level="L2",
            entity=instance,
            payload={
                "id": str(instance.id),
                "audit_prep_id": str(instance.audit_prep_id),
            },
        )


class AuditFindingViewSet(viewsets.ModelViewSet):
    queryset = AuditFinding.objects.select_related(
        "audit_prep__plant", "control_instance__control",
        "pdca_cycle", "closed_by", "lesson_learned",
    )
    serializer_class = AuditFindingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["audit_prep", "finding_type", "status", "audit_prep__plant"]
    search_fields = ["title", "description"]

    def perform_create(self, serializer):
        data = self.request.data
        # Resolve audit_date string to date object if needed
        from datetime import date
        audit_date_raw = data.get("audit_date")
        if isinstance(audit_date_raw, str):
            from dateutil import parser as dateparser
            try:
                audit_date = dateparser.parse(audit_date_raw).date()
            except Exception:
                audit_date = date.today()
        else:
            audit_date = audit_date_raw or date.today()

        finding = services.open_finding(
            audit_prep=serializer.validated_data["audit_prep"],
            finding_type=data.get("finding_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            audit_date=audit_date,
            user=self.request.user,
            control_instance=serializer.validated_data.get("control_instance"),
            auditor_name=data.get("auditor_name", ""),
        )
        # Attach the created instance so DRF can return it
        serializer.instance = finding

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .services import close_finding
        from apps.documents.models import Evidence
        from django.core.exceptions import ValidationError

        finding = self.get_object()
        notes = request.data.get("closure_notes", "")
        evidence_id = request.data.get("evidence_id")
        evidence = None
        if evidence_id:
            evidence = Evidence.objects.filter(pk=evidence_id).first()
        try:
            finding = close_finding(finding, request.user, notes, evidence)
            return Response({"ok": True, "status": finding.status})
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)


class AuditProgramViewSet(viewsets.ModelViewSet):
    queryset = AuditProgram.objects.select_related("plant", "framework", "approved_by")
    serializer_class = AuditProgramSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "framework", "year", "status"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="audit_prep.program.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "year": instance.year},
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="audit_prep.program.deleted",
            level="L2",
            entity=instance,
            payload={"title": instance.title, "year": instance.year},
        )
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from django.utils import timezone
        program = self.get_object()
        program.status = "approvato"
        program.approved_by = request.user
        program.approved_at = timezone.now()
        program.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        log_action(
            user=request.user,
            action_code="audit_prep.program.approved",
            level="L1",
            entity=program,
            payload={"year": program.year},
        )
        return Response({"ok": True, "status": program.status})

    @action(detail=True, methods=["post"], url_path="add-audit")
    def add_audit(self, request, pk=None):
        """Aggiunge o aggiorna un audit pianificato nel JSON array."""
        program = self.get_object()
        audit_entry = request.data.get("audit", {})
        if not audit_entry:
            return Response({"error": "Dati audit mancanti"}, status=400)
        planned = list(program.planned_audits)
        planned.append(audit_entry)
        program.planned_audits = planned
        program.save(update_fields=["planned_audits", "updated_at"])
        return Response({"ok": True, "planned_audits": program.planned_audits})

    @action(detail=False, methods=["post"], url_path="suggest")
    def suggest(self, request):
        """Genera piano annuale suggerito dal sistema."""
        from .services import suggest_audit_plan
        from apps.controls.models import Framework
        from apps.plants.models import Plant
        plant_id = request.data.get("plant")
        framework_codes = request.data.get("framework_codes", [])
        year = int(request.data.get("year", 2026))
        coverage_type = request.data.get("coverage_type", "campione")
        plant = Plant.objects.filter(pk=plant_id).first()
        frameworks = Framework.objects.filter(code__in=framework_codes)
        if not plant or not frameworks.exists():
            return Response({"error": "plant e framework_codes obbligatori"}, status=400)
        plan = suggest_audit_plan(plant, frameworks, year, coverage_type)
        return Response({"suggested_plan": plan})

    @action(detail=True, methods=["post"], url_path="launch-audit")
    def launch_audit(self, request, pk=None):
        """Lancia un AuditPrep da un audit pianificato."""
        from .services import launch_audit_from_program
        program = self.get_object()
        audit_id = request.data.get("audit_id")
        audit_entry = next(
            (a for a in program.planned_audits if a.get("id") == audit_id), None
        )
        if not audit_entry:
            return Response({"error": "Audit non trovato nel programma"}, status=404)
        if audit_entry.get("audit_prep_id"):
            return Response({"error": "Questo audit ha già un AuditPrep collegato"}, status=400)
        prep = launch_audit_from_program(program, audit_entry, request.user)
        return Response({
            "ok": True,
            "audit_prep_id": str(prep.pk),
            "controls_count": prep.evidence_items.count(),
        })

    @action(detail=True, methods=["post"], url_path="update-audit")
    def update_audit(self, request, pk=None):
        """Aggiorna un audit pianificato nel JSON."""
        program = self.get_object()
        audit_id = request.data.get("audit_id")
        updates = request.data.get("updates", {})
        audits = list(program.planned_audits)
        ALLOWED = ["title", "planned_date", "auditor_type", "auditor_name",
                   "scope_domains", "coverage_type", "notes", "status"]
        for a in audits:
            if a.get("id") == audit_id:
                for k, v in updates.items():
                    if k in ALLOWED:
                        a[k] = v
                break
        program.planned_audits = audits
        program.save(update_fields=["planned_audits", "updated_at"])
        return Response({"ok": True, "planned_audits": audits})

    @action(detail=True, methods=["post"], url_path="sync-completion")
    def sync_completion(self, request, pk=None):
        """Ricalcola % completamento dai AuditPrep reali."""
        from .services import sync_program_completion
        program = self.get_object()
        pct = sync_program_completion(program)
        return Response({"ok": True, "completion_pct": pct, "status": program.status})

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        """Relazione HTML del programma annuale."""
        from django.http import HttpResponse
        program = self.get_object()
        preps = AuditPrep.objects.filter(
            audit_program=program
        ).prefetch_related("evidence_items", "findings")

        rows = ""
        for audit in program.planned_audits:
            prep_id = audit.get("audit_prep_id")
            prep = preps.filter(pk=prep_id).first() if prep_id else None
            score = prep.readiness_score if prep else None
            status = audit.get("status", "planned")
            status_colors = {
                "planned": "#6b7280", "in_progress": "#2563eb",
                "completed": "#16a34a", "cancelled": "#dc2626",
            }
            color = status_colors.get(status, "#6b7280")
            rows += (
                f"<tr><td>Q{audit['quarter']}</td>"
                f"<td>{audit.get('title', '—')}</td>"
                f"<td>{', '.join(audit.get('framework_codes', []))}</td>"
                f"<td>{audit.get('planned_date', '—')}</td>"
                f"<td>{audit.get('auditor_name', '—')}</td>"
                f"<td style='color:{color};font-weight:bold'>{status.replace('_', ' ').title()}</td>"
                f"<td style='font-weight:bold'>{f'{score}/100' if score is not None else '—'}</td></tr>"
            )

        from django.utils import timezone as tz
        html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>Programma Audit {program.year}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:10px;margin:24px}}
h1{{font-size:16px;color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:6px}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}
th{{background:#1e40af;color:white;padding:5px 6px;text-align:left}}
td{{padding:4px 6px;border-bottom:1px solid #e5e7eb}}
tr:nth-child(even){{background:#f9fafb}}
</style></head><body>
<h1>Programma Audit Annuale {program.year}</h1>
<p><strong>Sito:</strong> {program.plant.name} &nbsp;
   <strong>Stato:</strong> {program.status} &nbsp;
   <strong>Completamento:</strong> {program.completion_pct}%</p>
<table>
<tr><th>Q</th><th>Titolo</th><th>Framework</th><th>Data</th><th>Auditor</th><th>Stato</th><th>Score</th></tr>
{rows}
</table></body></html>"""

        filename = f"ProgrammaAudit_{program.year}_{tz.now().strftime('%Y%m%d')}.html"
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
