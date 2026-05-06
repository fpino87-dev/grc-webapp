"""
Orchestrator del GRC Compliance Assistant.

Aggrega i risultati dei tool deterministici in una lista unificata di "gap"
prioritizzata, con CTA verso le pagine esistenti dell'app.
"""
from __future__ import annotations

from django.utils import timezone

from .agent_tools import (
    get_expired_documents,
    get_expired_risk_assessments,
    get_missing_evidences,
    get_suppliers_without_assessment,
)

PRIORITY_BASE = {
    "document_expired":             90,
    "document_review_due":          50,
    "control_missing_doc":          70,
    "control_missing_evidence":     70,
    "control_expired_evidence":     80,
    "control_status_gap":           75,
    "control_status_partial":       60,
    "control_not_evaluated":        50,
    "risk_expired":                 75,
    "risk_needs_revaluation":       85,
    "supplier_never_assessed":      80,
    "supplier_assessment_expired":  70,
}


_CONTROL_STATUS_FALLBACK = {
    "gap":          ("control_status_gap",     "Marcato come gap (in attesa di rimedio)"),
    "parziale":     ("control_status_partial", "Compliance parziale"),
    "non_valutato": ("control_not_evaluated",  "Mai valutato"),
}


def _urgency(days_overdue: int | None, base: int) -> str:
    if days_overdue is not None and days_overdue >= 30:
        return "red"
    if base >= 80:
        return "red"
    if base >= 60:
        return "yellow"
    return "green"


def build_gaps(user, plant_id) -> tuple[list[dict], int]:
    """Costruisce la lista unificata e prioritizzata di gap. Tronca a 20."""
    today = timezone.now().date()
    gaps: list[dict] = []

    # 1. Documenti
    for d in get_expired_documents(user, plant_id, today):
        gap_kind = "document_expired" if d["kind"] == "expired" else "document_review_due"
        base = PRIORITY_BASE[gap_kind]
        days = d.get("days_overdue") or 0
        gaps.append({
            "kind": gap_kind,
            "category": "documents",
            "ref_id": d["id"],
            "title": d["title"],
            "subtitle": (
                f"Scaduto da {days} giorni" if gap_kind == "document_expired"
                else f"Revisione richiesta da {days} giorni"
            ),
            "details": d,
            "priority_score": base + min(days, 30),
            "urgency": _urgency(days, base),
            "frontend_url": d["frontend_url"],
        })

    # 2. Controlli non-compliant e non-N/A
    # Priorita' alle carenze concrete (evidenze/documenti); fallback allo
    # status field se non ci sono dettagli specifici da check_evidence_requirements.
    for c in get_missing_evidences(user, plant_id):
        if c["expired_evidences"]:
            kind = "control_expired_evidence"
            sub = f"{len(c['expired_evidences'])} evidenza/e scadute"
        elif c["missing_evidences"]:
            kind = "control_missing_evidence"
            sub = f"{len(c['missing_evidences'])} evidenza/e mancanti"
        elif c["missing_documents"]:
            kind = "control_missing_doc"
            sub = f"{len(c['missing_documents'])} documento/i mancante/i"
        else:
            fallback = _CONTROL_STATUS_FALLBACK.get(c.get("status", ""))
            if not fallback:
                continue
            kind, sub = fallback
        base = PRIORITY_BASE[kind]
        gaps.append({
            "kind": kind,
            "category": "controls",
            "ref_id": c["control_instance_id"],
            "title": f"{c['control_external_id']} — {c['control_title']}",
            "subtitle": f"{c['framework_code']}: {sub}",
            "details": c,
            "priority_score": base,
            "urgency": _urgency(None, base),
            "frontend_url": c["frontend_url"],
        })

    # 3. Risk assessment
    for r in get_expired_risk_assessments(user, plant_id, today):
        kind = "risk_needs_revaluation" if r["reason"] == "needs_revaluation" else "risk_expired"
        base = PRIORITY_BASE[kind]
        days = r.get("days_overdue") or 0
        gaps.append({
            "kind": kind,
            "category": "risk",
            "ref_id": r["id"],
            "title": r["name"],
            "subtitle": (
                "Richiede rivalutazione (change recente)" if kind == "risk_needs_revaluation"
                else f"Assessment scaduto da {days} giorni"
            ),
            "details": r,
            "priority_score": base + min(days, 30),
            "urgency": _urgency(days, base),
            "frontend_url": r["frontend_url"],
        })

    # 4. Fornitori
    for s in get_suppliers_without_assessment(user, plant_id, today):
        kind = "supplier_never_assessed" if s["reason"] == "never_assessed" else "supplier_assessment_expired"
        base = PRIORITY_BASE[kind]
        days = s.get("days_overdue") or 0
        gaps.append({
            "kind": kind,
            "category": "suppliers",
            "ref_id": s["id"],
            "title": s["name"],
            "subtitle": (
                "Mai valutato (NIS2 / alto rischio)" if kind == "supplier_never_assessed"
                else f"Assessment scaduto da {days} giorni"
            ),
            "details": s,
            "priority_score": base + min(days, 30),
            "urgency": _urgency(days, base),
            "frontend_url": s["frontend_url"],
        })

    gaps.sort(key=lambda g: (-g["priority_score"], g["title"]))
    total = len(gaps)
    return gaps[:20], total


def build_summary(user, plant_id) -> dict:
    """Sintesi numerica: counts per framework attivo + plant info."""
    from apps.controls.services import get_compliance_summary
    from apps.plants.models import Plant
    from apps.plants.services import get_active_frameworks

    plant = Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()
    frameworks = []
    if plant:
        for fw in get_active_frameworks(plant):
            s = get_compliance_summary(plant_id, fw.code)
            frameworks.append({
                "code": fw.code,
                "name": fw.name,
                **s,
            })
    return {
        "plant_id": str(plant_id),
        "plant_name": plant.name if plant else "",
        "frameworks": frameworks,
    }


def build_explanation_prompt(gap: dict) -> tuple[str, str]:
    """Costruisce (prompt, system) per chiedere all'LLM una spiegazione del gap."""
    system = (
        "Sei un consulente GRC. Spiega in italiano semplice e diretto a un "
        "responsabile aziendale (non tecnico) cosa significa questo gap di "
        "compliance, perche' conta, e quali sono i passi concreti per chiuderlo. "
        "Massimo 5 frasi. Non aggiungere disclaimer."
    )
    kind = gap.get("kind", "")
    title = gap.get("title", "")
    subtitle = gap.get("subtitle", "")
    details = gap.get("details", {}) or {}
    prompt = (
        "GAP DI COMPLIANCE\n"
        f"Tipo: {kind}\n"
        f"Titolo: {title}\n"
        f"Stato: {subtitle}\n\n"
        "DATI:\n"
        f"{_format_details(details)}\n\n"
        "Spiega cosa significa, perche' e' un problema, e i passi concreti per chiuderlo."
    )
    return prompt, system


def _format_details(details: dict) -> str:
    """Format leggibile dei details, escludendo PII."""
    safe_keys = {
        "control_external_id", "control_title", "framework_code", "status",
        "document_type", "expiry_date", "review_due_date", "days_overdue",
        "missing_documents", "missing_evidences", "expired_evidences",
        "risk_level", "nis2_relevant", "reason", "next_due",
        "assessment_type", "score",
    }
    lines = []
    for k, v in details.items():
        if k not in safe_keys:
            continue
        if isinstance(v, list) and v:
            lines.append(f"- {k}: {len(v)} elementi")
        elif v not in (None, "", []):
            lines.append(f"- {k}: {v}")
    return "\n".join(lines) or "- (nessun dettaglio aggiuntivo)"
