"""
Audit pack builder — esporta in un singolo ZIP tutto il materiale richiesto da
un auditor di terza parte (TISAX/ISO/NIS2).

Il pack include 9 cartelle (subset selezionabile via `scope`):

    00_README.md                 sommario, framework espansi, scope
    01_controls/                 stato + maturity per ogni control instance
    02_documents/                policy/procedure approvate (file binari)
    03_risk_register.xlsx        (placeholder CSV se openpyxl assente)
    04_bia_bcp/                  processi critici + piani BCP + ultimi test
    05_incidents/                incidenti del plant
    06_audit_trail.csv           log eventi rilevanti (filtrato sugli entity)
    07_training_competencies.csv enrollment + competenze
    08_governance/               role assignment + comitati sicurezza
    09_management_review/        ultima review approvata + delibere + actions
    manifest.json                sha256 di ogni file (tamper evidence)

Espansione framework TISAX:
    L2     -> [L2]
    L3     -> [L2, L3]            (L3 estende L2)
    PROTO  -> [L2, L3, PROTO]     (Prototype Protection presuppone IS L2+L3)

Uso tipico:
    pack = build_audit_pack(
        plant=plant,
        frameworks=["TISAX_L3"],
        scope=["controls","documents","risk","management_review"],
        user=request.user,
    )

`pack` e' un `Path` al file ZIP generato. La dimensione puo' raggiungere
centinaia di MB su plant con molti documenti binari -> chiamare sempre da
Celery, mai da view sincrona.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .framework_hierarchy import expand_tisax

logger = logging.getLogger(__name__)

__all__ = ["build_audit_pack", "expand_tisax"]


# Categorie di scope ammesse: ogni `_collect_*` produce file in una sotto
# cartella. L'ordine e' stabile per riproducibilita' del manifest.
SCOPE_CATEGORIES = (
    "controls",
    "documents",
    "evidences",
    "risk",
    "bia_bcp",
    "incidents",
    "training",
    "governance",
    "management_review",
    "audit_trail",
)


def _media_path(relative: str) -> Optional[Path]:
    """Risolve un path relativo allo storage media; None se non esiste."""
    if not relative:
        return None
    full = Path(settings.MEDIA_ROOT) / relative
    return full if full.exists() else None


def _safe_filename(s: str) -> str:
    """Sanitize per uso nel filesystem (rimuove / e caratteri ambigui)."""
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in s)[:120]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def _collect_controls(out_dir: Path, plant, frameworks: list[str]) -> dict:
    """Stato di ogni ControlInstance del plant per i framework dati."""
    from apps.controls.models import ControlInstance

    controls_dir = out_dir / "01_controls"
    controls_dir.mkdir(parents=True, exist_ok=True)

    qs = (
        ControlInstance.objects
        .filter(
            plant=plant,
            control__framework__code__in=frameworks,
            deleted_at__isnull=True,
        )
        .select_related("control__framework", "control__domain", "owner")
        .order_by("control__framework__code", "control__external_id")
    )

    rows: list[dict] = []
    for inst in qs:
        rows.append({
            "framework": inst.control.framework.code,
            "external_id": inst.control.external_id,
            "title": inst.control.get_title("it") if hasattr(inst.control, "get_title") else "",
            "domain": getattr(inst.control.domain, "code", "") or "",
            "status": inst.status,
            "maturity_level": getattr(inst, "maturity_level", None),
            "owner": (inst.owner.email if inst.owner else ""),
            "last_evaluated_at": inst.updated_at.isoformat() if inst.updated_at else "",
            "note": getattr(inst, "note", "") or "",
        })

    csv_path = controls_dir / "controls_status.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        if rows:
            writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            fp.write("# Nessun controllo trovato per i framework richiesti.\n")

    summary = {
        "framework_breakdown": {},
        "status_breakdown": {},
        "total": len(rows),
    }
    for r in rows:
        summary["framework_breakdown"][r["framework"]] = (
            summary["framework_breakdown"].get(r["framework"], 0) + 1
        )
        summary["status_breakdown"][r["status"]] = (
            summary["status_breakdown"].get(r["status"], 0) + 1
        )

    (controls_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return summary


def _collect_documents(out_dir: Path, plant, frameworks: list[str]) -> dict:
    """Documenti approvati del plant (policy/procedure/manuali) con file binari."""
    from apps.documents.models import Document, DocumentVersion
    from django.db.models import Q

    docs_dir = out_dir / "02_documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    qs = (
        Document.objects
        .filter(deleted_at__isnull=True, status="approvato")
        .filter(Q(plant=plant) | Q(shared_plants=plant) | Q(plant__isnull=True))
        .distinct()
    )

    index_rows: list[dict] = []
    copied = 0
    skipped_missing = 0
    for doc in qs:
        last_version = (
            DocumentVersion.objects
            .filter(document=doc, deleted_at__isnull=True)
            .order_by("-version_number").first()
        )
        if not last_version:
            continue
        src = _media_path(last_version.storage_path)
        target_name = f"{_safe_filename(doc.title)}__v{last_version.version_number}__{_safe_filename(last_version.file_name)}"
        target = docs_dir / target_name

        if src:
            shutil.copy2(src, target)
            copied += 1
        else:
            target.write_text(
                f"FILE NON TROVATO IN STORAGE: {last_version.storage_path}\n",
                encoding="utf-8",
            )
            skipped_missing += 1

        index_rows.append({
            "title": doc.title,
            "category": doc.category,
            "document_type": doc.document_type,
            "version": last_version.version_number,
            "approved_at": doc.approved_at.isoformat() if doc.approved_at else "",
            "expiry_date": str(doc.expiry_date) if doc.expiry_date else "",
            "owner": (doc.owner.email if doc.owner else ""),
            "approver": (doc.approver.email if doc.approver else ""),
            "filename": target_name,
            "sha256_documented": last_version.sha256 or "",
            "missing_file": (src is None),
        })

    csv_path = docs_dir / "_index.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        if index_rows:
            writer = csv.DictWriter(fp, fieldnames=list(index_rows[0].keys()))
            writer.writeheader()
            writer.writerows(index_rows)
        else:
            fp.write("# Nessun documento approvato per il plant.\n")

    return {
        "documents_indexed": len(index_rows),
        "files_copied": copied,
        "files_missing": skipped_missing,
    }


def _collect_evidences(out_dir: Path, plant, frameworks: list[str]) -> dict:
    """Evidenze collegate ai control instance del plant."""
    from apps.documents.models import Evidence

    ev_dir = out_dir / "02b_evidences"
    ev_dir.mkdir(parents=True, exist_ok=True)

    qs = Evidence.objects.filter(deleted_at__isnull=True, plant=plant)

    rows: list[dict] = []
    copied = 0
    skipped_missing = 0
    for ev in qs:
        src = _media_path(ev.file_path) if ev.file_path else None
        target_name = f"{_safe_filename(ev.title)}__{_safe_filename(str(ev.pk)[:8])}"
        if src:
            target_name += src.suffix
            shutil.copy2(src, ev_dir / target_name)
            copied += 1
        else:
            target_name += ".missing.txt"
            (ev_dir / target_name).write_text(
                f"FILE NON TROVATO: {ev.file_path or '(nessun path)'}\n",
                encoding="utf-8",
            )
            skipped_missing += 1
        rows.append({
            "title": ev.title,
            "type": ev.evidence_type,
            "valid_until": str(ev.valid_until) if ev.valid_until else "",
            "uploaded_by": (ev.uploaded_by.email if ev.uploaded_by else ""),
            "filename": target_name,
        })

    csv_path = ev_dir / "_index.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        if rows:
            writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            fp.write("# Nessuna evidenza per il plant.\n")

    return {
        "evidences_total": len(rows),
        "files_copied": copied,
        "files_missing": skipped_missing,
    }


def _collect_risk(out_dir: Path, plant) -> dict:
    """Risk register completato del plant."""
    from apps.risk.models import RiskAssessment

    risk_dir = out_dir / "03_risk"
    risk_dir.mkdir(parents=True, exist_ok=True)

    qs = (
        RiskAssessment.objects
        .filter(plant=plant, deleted_at__isnull=True, status="completato")
        .select_related("owner")
        .order_by("-score")
    )
    rows = [{
        "name": r.name,
        "threat_category": r.threat_category,
        "probability": r.probability,
        "impact": r.impact,
        "score": r.score,
        "inherent_score": r.inherent_score,
        "treatment": r.treatment,
        "nis2_relevance": r.nis2_relevance,
        "nis2_art21_category": r.nis2_art21_category,
        "owner": (r.owner.email if r.owner else ""),
        "risk_accepted_formally": r.risk_accepted_formally,
        "needs_revaluation": r.needs_revaluation,
        "completed_at": r.updated_at.isoformat() if r.updated_at else "",
    } for r in qs]

    csv_path = risk_dir / "risk_register.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        if rows:
            writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            fp.write("# Nessun risk assessment completato per il plant.\n")

    return {"total": len(rows)}


def _collect_bia_bcp(out_dir: Path, plant) -> dict:
    """Processi critici BIA + piani BCP + ultimo test."""
    from apps.bia.models import CriticalProcess
    from apps.bcp.models import BcpPlan, BcpTest

    bia_dir = out_dir / "04_bia_bcp"
    bia_dir.mkdir(parents=True, exist_ok=True)

    procs = list(CriticalProcess.objects.filter(plant=plant, deleted_at__isnull=True))
    bia_rows = [{
        "name": p.name,
        "criticality": p.criticality,
        "rto_target_hours": p.rto_target_hours,
        "rpo_target_hours": p.rpo_target_hours,
        "owner": (p.owner.email if p.owner else ""),
        "status": getattr(p, "status", ""),
    } for p in procs]
    with (bia_dir / "critical_processes.csv").open("w", newline="", encoding="utf-8") as fp:
        if bia_rows:
            w = csv.DictWriter(fp, fieldnames=list(bia_rows[0].keys()))
            w.writeheader(); w.writerows(bia_rows)
        else:
            fp.write("# Nessun processo critico per il plant.\n")

    plans = list(
        BcpPlan.objects.filter(plant=plant, deleted_at__isnull=True)
        .select_related("critical_process")
    )
    bcp_rows = []
    for plan in plans:
        last_test = (
            BcpTest.objects.filter(plan=plan, deleted_at__isnull=True)
            .order_by("-test_date").first()
        )
        bcp_rows.append({
            "title": plan.title,
            "critical_process": (plan.critical_process.name if plan.critical_process else ""),
            "status": plan.status,
            "next_test_date": str(plan.next_test_date) if plan.next_test_date else "",
            "last_test_date": str(last_test.test_date) if last_test else "",
            "last_test_result": (last_test.result if last_test else ""),
        })
    with (bia_dir / "bcp_plans.csv").open("w", newline="", encoding="utf-8") as fp:
        if bcp_rows:
            w = csv.DictWriter(fp, fieldnames=list(bcp_rows[0].keys()))
            w.writeheader(); w.writerows(bcp_rows)
        else:
            fp.write("# Nessun piano BCP per il plant.\n")

    return {"critical_processes": len(bia_rows), "bcp_plans": len(bcp_rows)}


def _collect_incidents(out_dir: Path, plant, since: Optional[date]) -> dict:
    from apps.incidents.models import Incident

    inc_dir = out_dir / "05_incidents"
    inc_dir.mkdir(parents=True, exist_ok=True)

    qs = Incident.objects.filter(plant=plant, deleted_at__isnull=True)
    if since:
        qs = qs.filter(detection_date__gte=since)

    rows = [{
        "title": i.title,
        "severity": i.severity,
        "status": i.status,
        "detection_date": str(i.detection_date) if getattr(i, "detection_date", None) else "",
        "closed_at": i.closed_at.isoformat() if getattr(i, "closed_at", None) else "",
        "nis2_notifiable": getattr(i, "nis2_notifiable", ""),
        "category": getattr(i, "category", ""),
    } for i in qs]
    with (inc_dir / "incidents.csv").open("w", newline="", encoding="utf-8") as fp:
        if rows:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        else:
            fp.write("# Nessun incidente per il plant nel periodo richiesto.\n")
    return {"total": len(rows)}


def _collect_training(out_dir: Path, plant) -> dict:
    from apps.training.models import TrainingEnrollment

    tr_dir = out_dir / "07_training"
    tr_dir.mkdir(parents=True, exist_ok=True)

    qs = (
        TrainingEnrollment.objects
        .filter(deleted_at__isnull=True)
        .select_related("user", "course")
    )
    rows = [{
        "user": (e.user.email if e.user else ""),
        "course": (e.course.title if e.course else ""),
        "status": e.status,
        "completion_date": str(e.completion_date) if getattr(e, "completion_date", None) else "",
        "score": getattr(e, "score", None),
    } for e in qs]
    with (tr_dir / "training_enrollments.csv").open("w", newline="", encoding="utf-8") as fp:
        if rows:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        else:
            fp.write("# Nessuna iscrizione training trovata.\n")
    return {"total": len(rows)}


def _collect_governance(out_dir: Path, plant) -> dict:
    from apps.governance.models import RoleAssignment, SecurityCommittee

    gov_dir = out_dir / "08_governance"
    gov_dir.mkdir(parents=True, exist_ok=True)

    today = timezone.now().date()
    role_rows = []
    for ra in RoleAssignment.objects.filter(deleted_at__isnull=True):
        valid = (ra.valid_from is None or ra.valid_from <= today) and (
            ra.valid_until is None or ra.valid_until >= today
        )
        role_rows.append({
            "user": (ra.user.email if ra.user else ""),
            "role": ra.role,
            "valid_from": str(ra.valid_from) if ra.valid_from else "",
            "valid_until": str(ra.valid_until) if ra.valid_until else "",
            "is_currently_active": valid,
        })
    with (gov_dir / "role_assignments.csv").open("w", newline="", encoding="utf-8") as fp:
        if role_rows:
            w = csv.DictWriter(fp, fieldnames=list(role_rows[0].keys()))
            w.writeheader(); w.writerows(role_rows)
        else:
            fp.write("# Nessuna assegnazione ruolo.\n")

    committees = list(SecurityCommittee.objects.filter(deleted_at__isnull=True))
    com_rows = [{
        "name": c.name,
        "purpose": getattr(c, "purpose", ""),
        "frequency": getattr(c, "frequency", ""),
    } for c in committees]
    with (gov_dir / "security_committees.csv").open("w", newline="", encoding="utf-8") as fp:
        if com_rows:
            w = csv.DictWriter(fp, fieldnames=list(com_rows[0].keys()))
            w.writeheader(); w.writerows(com_rows)
        else:
            fp.write("# Nessun comitato di sicurezza definito.\n")

    return {"role_assignments": len(role_rows), "committees": len(com_rows)}


def _collect_management_review(out_dir: Path, plant) -> dict:
    """Solo review APPROVATE (snapshot di direzione formale)."""
    from apps.management_review.models import ManagementReview, ReviewAction

    mr_dir = out_dir / "09_management_review"
    mr_dir.mkdir(parents=True, exist_ok=True)

    qs = (
        ManagementReview.objects
        .filter(plant=plant, deleted_at__isnull=True, approval_status="approvato")
        .order_by("-review_date")
    )

    if not qs.exists():
        (mr_dir / "NO_APPROVED_REVIEW.txt").write_text(
            "Nessuna revisione di direzione approvata per questo plant alla data del pack.\n",
            encoding="utf-8",
        )
        return {"reviews_approved": 0, "actions_total": 0}

    review_rows: list[dict] = []
    action_rows: list[dict] = []
    for r in qs:
        review_rows.append({
            "title": r.title,
            "review_date": str(r.review_date),
            "chair": (r.chair.email if r.chair else ""),
            "approval_status": r.approval_status,
            "approved_at": r.approved_at.isoformat() if r.approved_at else "",
            "approved_by": (r.approved_by.email if r.approved_by else ""),
            "next_review_date": str(r.next_review_date) if r.next_review_date else "",
            "delibere_count": len(r.delibere or []),
        })
        # Snapshot completo di ogni review (agenda, kpi, delibere) come JSON
        review_payload = {
            "title": r.title,
            "review_date": str(r.review_date),
            "chair": (r.chair.email if r.chair else None),
            "attendees": list(r.attendees.values_list("email", flat=True)),
            "agenda": r.agenda,
            "kpi_snapshot": r.kpi_snapshot,
            "delibere": r.delibere,
            "snapshot_data": r.snapshot_data,
            "approval_status": r.approval_status,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "approved_by": (r.approved_by.email if r.approved_by else None),
            "approval_note": r.approval_note,
        }
        review_file = mr_dir / f"review_{r.review_date}_{_safe_filename(r.title)}.json"
        review_file.write_text(
            json.dumps(review_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        for act in ReviewAction.objects.filter(review=r, deleted_at__isnull=True):
            action_rows.append({
                "review_date": str(r.review_date),
                "review_title": r.title,
                "description": act.description,
                "owner": (act.owner.email if act.owner else ""),
                "due_date": str(act.due_date) if act.due_date else "",
                "status": act.status,
                "closed_at": act.closed_at.isoformat() if act.closed_at else "",
            })

    with (mr_dir / "_index.csv").open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=list(review_rows[0].keys()))
        w.writeheader(); w.writerows(review_rows)
    with (mr_dir / "actions.csv").open("w", newline="", encoding="utf-8") as fp:
        if action_rows:
            w = csv.DictWriter(fp, fieldnames=list(action_rows[0].keys()))
            w.writeheader(); w.writerows(action_rows)
        else:
            fp.write("# Nessuna action item nelle review approvate.\n")

    return {"reviews_approved": len(review_rows), "actions_total": len(action_rows)}


def _collect_audit_trail(out_dir: Path, plant, since: Optional[date]) -> dict:
    """Audit trail filtrato per gli entity_id collegati al plant."""
    from core.audit import AuditLog

    at_dir = out_dir / "06_audit_trail"
    at_dir.mkdir(parents=True, exist_ok=True)

    qs = AuditLog.objects.all()
    if since:
        qs = qs.filter(timestamp_utc__date__gte=since)

    # Senza una FK diretta a plant nell'AuditLog, ci limitiamo a esportare gli
    # eventi i cui entity_id corrispondono ai modelli plant-scoped del plant.
    plant_entity_ids: set[str] = {str(plant.pk)}

    from apps.controls.models import ControlInstance
    from apps.documents.models import Document, Evidence
    from apps.incidents.models import Incident
    from apps.risk.models import RiskAssessment

    plant_entity_ids |= set(map(str, ControlInstance.objects.filter(plant=plant).values_list("pk", flat=True)))
    plant_entity_ids |= set(map(str, Document.objects.filter(plant=plant).values_list("pk", flat=True)))
    plant_entity_ids |= set(map(str, Evidence.objects.filter(plant=plant).values_list("pk", flat=True)))
    plant_entity_ids |= set(map(str, Incident.objects.filter(plant=plant).values_list("pk", flat=True)))
    plant_entity_ids |= set(map(str, RiskAssessment.objects.filter(plant=plant).values_list("pk", flat=True)))

    qs = qs.filter(entity_id__in=plant_entity_ids).order_by("timestamp_utc")
    rows = [{
        "timestamp_utc": l.timestamp_utc.isoformat(),
        "user_email_at_time": l.user_email_at_time,  # gia' pseudonimizzata
        "action_code": l.action_code,
        "level": l.level,
        "entity_type": l.entity_type,
        "entity_id": str(l.entity_id),
        "record_hash": l.record_hash,
        "hash_version": l.hash_version,
    } for l in qs]
    with (at_dir / "audit_trail.csv").open("w", newline="", encoding="utf-8") as fp:
        if rows:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        else:
            fp.write("# Nessun evento audit trail correlato al plant nel periodo.\n")
    return {"records": len(rows)}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_COLLECTORS = {
    "controls": lambda d, p, fw, since: _collect_controls(d, p, fw),
    "documents": lambda d, p, fw, since: _collect_documents(d, p, fw),
    "evidences": lambda d, p, fw, since: _collect_evidences(d, p, fw),
    "risk": lambda d, p, fw, since: _collect_risk(d, p),
    "bia_bcp": lambda d, p, fw, since: _collect_bia_bcp(d, p),
    "incidents": lambda d, p, fw, since: _collect_incidents(d, p, since),
    "training": lambda d, p, fw, since: _collect_training(d, p),
    "governance": lambda d, p, fw, since: _collect_governance(d, p),
    "management_review": lambda d, p, fw, since: _collect_management_review(d, p),
    "audit_trail": lambda d, p, fw, since: _collect_audit_trail(d, p, since),
}


def build_audit_pack(
    *,
    plant,
    frameworks: list[str],
    scope: list[str],
    user,
    since: Optional[date] = None,
    output_dir: Optional[Path] = None,
) -> tuple[Path, dict]:
    """
    Genera lo ZIP del pack. Restituisce `(zip_path, summary_dict)`.

    `output_dir` default a `BACKUP_DIR/audit_packs/`. Il file e' nominato
    `audit_pack_{plant_code}_{timestamp}.zip` ed e' tracciato nel manifest
    interno con SHA-256 di ogni file.
    """
    expanded = expand_tisax(frameworks)
    selected_scope = [s for s in SCOPE_CATEGORIES if s in (scope or [])] or list(SCOPE_CATEGORIES)

    if output_dir is None:
        output_dir = Path(getattr(settings, "BACKUP_DIR", "/app/backups")) / "audit_packs"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    plant_code = _safe_filename(getattr(plant, "code", str(plant.pk)))
    zip_filename = f"audit_pack_{plant_code}_{ts}.zip"
    zip_path = output_dir / zip_filename

    # Lavoriamo in temp dir poi zippiamo: cosi' il manifest puo' essere
    # calcolato sui file effettivi prima della compressione.
    summary: dict = {
        "generated_at": timezone.now().isoformat(),
        "generated_by": getattr(user, "email", "") or "",
        "plant": {"id": str(plant.pk), "code": getattr(plant, "code", ""), "name": getattr(plant, "name", "")},
        "frameworks_requested": frameworks,
        "frameworks_expanded": expanded,
        "scope": selected_scope,
        "since": str(since) if since else None,
        "categories": {},
    }

    with tempfile.TemporaryDirectory(prefix="audit_pack_") as tmp:
        tmp_path = Path(tmp)
        for cat in selected_scope:
            collector = _COLLECTORS.get(cat)
            if not collector:
                continue
            try:
                summary["categories"][cat] = collector(tmp_path, plant, expanded, since)
            except Exception as exc:  # pragma: no cover — registrato e proseguiamo
                logger.exception("audit_pack: collector %s fallito", cat)
                summary["categories"][cat] = {"error": str(exc)[:500]}

        # README
        readme_lines = [
            "# Audit Pack",
            "",
            f"- **Generato il**: {summary['generated_at']}",
            f"- **Plant**: {summary['plant']['name']} ({summary['plant']['code']})",
            f"- **Framework richiesti**: {', '.join(frameworks) or '(nessuno)'}",
            f"- **Framework espansi (gerarchia TISAX)**: {', '.join(expanded) or '(nessuno)'}",
            f"- **Scope**: {', '.join(selected_scope)}",
            f"- **Filtro temporale (since)**: {summary['since'] or 'nessuno'}",
            "",
            "## Contenuto",
            "",
        ]
        for cat, info in summary["categories"].items():
            readme_lines.append(f"- `{cat}`: {json.dumps(info, ensure_ascii=False)}")
        readme_lines.append("")
        readme_lines.append("Il `manifest.json` contiene lo SHA-256 di ogni file: ")
        readme_lines.append("ricalcolando lo stesso hash sul file ricevuto si verifica l'integrita'.")
        (tmp_path / "00_README.md").write_text("\n".join(readme_lines), encoding="utf-8")

        # Manifest sha256 di ogni file
        manifest = {
            "version": 1,
            "generated_at": summary["generated_at"],
            "files": [],
        }
        for f in sorted(tmp_path.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(tmp_path))
                manifest["files"].append({
                    "path": rel,
                    "size_bytes": f.stat().st_size,
                    "sha256": _sha256_file(f),
                })
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
        )

        # Compressione ZIP
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(tmp_path.rglob("*")):
                if f.is_file():
                    zf.write(f, arcname=str(f.relative_to(tmp_path)))

    summary["zip_path"] = str(zip_path)
    summary["zip_size_bytes"] = zip_path.stat().st_size
    summary["zip_sha256"] = _sha256_file(zip_path)
    return zip_path, summary
