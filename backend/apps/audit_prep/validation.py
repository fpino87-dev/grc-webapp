"""
Auto-validazione dell'AuditPrep.

Cicla tutti gli `EvidenceItem` del prep e per ognuno valuta lo stato del
control_instance collegato sulla base di evidenze, documenti e finding aperti.

Regole:
    presente:  >= 1 evidenza valida (valid_until >= oggi)
               AND >= 1 documento approvato (no expiry o expiry >= oggi)
               AND nessun major_nc aperto
    scaduto:   esistono evidenze o documenti ma TUTTI scaduti
    mancante:  nessuna evidenza valida e nessun documento approvato

Per `mancante` e `scaduto` viene aperto un AuditFinding `minor_nc`
(`auto_generated=True`). L'operazione e' idempotente: se per lo stesso
control_instance esiste gia' un finding auto-generato `open`/`in_response`
non si crea un duplicato.

Le condizioni "tutto a posto" descritte dal prodotto: documenti presenti
e non scaduti, evidenze ok, nessun major aperto -> control compliant.
In caso contrario il sistema apre il finding del mancante / scaduto, che
poi l'utente potra' rivedere o chiudere normalmente.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.audit import log_action

from .framework_hierarchy import expand_tisax
from .models import AuditFinding, AuditPrep, EvidenceItem
from .services import open_finding, update_readiness_score

logger = logging.getLogger(__name__)


def _detect_missing_extended_frameworks(prep: AuditPrep) -> dict | None:
    """
    Se il prep e' su un framework gerarchico (TISAX_L3/PROTO) e mancano
    EvidenceItem dei livelli inferiori implicati, restituisce un payload di
    warning. None se tutto OK (o framework non gerarchico).
    """
    if not prep.framework_id:
        return None
    code = prep.framework.code
    expanded = expand_tisax([code])
    if len(expanded) <= 1:
        return None

    covered_codes = set(
        prep.evidence_items
        .filter(deleted_at__isnull=True, control_instance__isnull=False)
        .values_list("control_instance__control__framework__code", flat=True)
    )
    missing = [c for c in expanded if c not in covered_codes]
    if not missing:
        return None
    return {
        "code": "missing_extended_controls",
        "framework_requested": code,
        "frameworks_expanded": expanded,
        "missing_frameworks": missing,
        "hint": (
            "Il prep e' su un framework gerarchico (L3/PROTO) ma non contiene "
            "EvidenceItem per i livelli implicati. Usa 'sync-controls' per "
            "allineare prima della validazione."
        ),
    }


def _collect_validation_sources(ci):
    """
    Restituisce le `ControlInstance` da considerare come fonti valide per
    questo controllo: l'istanza stessa + gli extender (controlli che la
    estendono via `ControlMapping(relationship="extends")`, es. TISAX L3
    estende L2 — un'evidenza L3 vale anche per L2).

    La direzione e' una sola: L3 -> L2 (chi estende copre l'esteso). L'inverso
    non vale: un'evidenza L2 non sostituisce un L3 piu' stringente.

    La regola di estensione vive in `apps.controls.services.get_extender_instances`
    (single source of truth condivisa con il GRC Assistant).
    """
    from apps.controls.services import get_extender_instances

    return [ci, *get_extender_instances(ci)]


def _evaluate_evidence_item(item: EvidenceItem) -> tuple[str, list[str]]:
    """
    Restituisce `(new_status, reasons)` dove `new_status` e' uno tra
    "presente" / "scaduto" / "mancante". `reasons` e' una lista di
    bullet che spiega perche' (utile per audit log e UI).
    """
    from apps.controls.models import ControlInstance
    from apps.documents.models import Document, Evidence

    today = timezone.now().date()
    ci = item.control_instance
    reasons: list[str] = []

    if ci is None:
        return "mancante", ["Evidence item non collegato a nessun control_instance"]

    sources = _collect_validation_sources(ci)
    source_ci_ids = [s.pk for s in sources]
    extender_codes = [
        s.control.external_id for s in sources if s.pk != ci.pk
    ]

    # Evidenza "valida" = senza scadenza (= permanente) oppure non ancora scaduta.
    valid_evidences = Evidence.objects.filter(
        control_instances__in=source_ci_ids,
        deleted_at__isnull=True,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).distinct()
    has_valid_evidence = valid_evidences.exists()

    expired_evidences = Evidence.objects.filter(
        control_instances__in=source_ci_ids,
        deleted_at__isnull=True,
        valid_until__isnull=False,
        valid_until__lt=today,
    ).distinct()
    has_expired_evidence = expired_evidences.exists()

    # Documento "valido" = approvato + (no expiry oppure expiry futura).
    valid_docs = Document.objects.filter(
        control_refs__in=source_ci_ids,
        deleted_at__isnull=True,
        status="approvato",
    ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)).distinct()
    has_valid_doc = valid_docs.exists()

    expired_docs = Document.objects.filter(
        control_refs__in=source_ci_ids,
        deleted_at__isnull=True,
        status="approvato",
        expiry_date__isnull=False,
        expiry_date__lt=today,
    ).distinct()
    has_expired_doc = expired_docs.exists()

    open_major = AuditFinding.objects.filter(
        control_instance=ci,
        finding_type="major_nc",
        status__in=["open", "in_response"],
        deleted_at__isnull=True,
    ).exists()

    if open_major:
        reasons.append("Major NC aperto sul control")
        return "mancante", reasons

    if has_valid_evidence and has_valid_doc:
        reasons.append(f"{valid_evidences.count()} evidenza/e valida/e")
        reasons.append(f"{valid_docs.count()} documento/i approvato/i e validi")
        if extender_codes:
            reasons.append(
                "Coperto anche da controlli estendenti: " + ", ".join(extender_codes)
            )
        return "presente", reasons

    if has_expired_evidence or has_expired_doc:
        if has_expired_evidence:
            reasons.append(f"{expired_evidences.count()} evidenza/e scaduta/e")
        if has_expired_doc:
            reasons.append(f"{expired_docs.count()} documento/i scaduto/i")
        if not has_valid_evidence:
            reasons.append("nessuna evidenza ancora valida")
        if not has_valid_doc:
            reasons.append("nessun documento approvato ancora valido")
        return "scaduto", reasons

    reasons.append("nessuna evidenza valida")
    reasons.append("nessun documento approvato")
    return "mancante", reasons


def _has_open_finding(control_instance, audit_prep) -> bool:
    """True se esiste gia' un finding aperto (manuale o auto-generato) per
    questo control nello stesso prep. Evita duplicati: se l'auditor ha gia'
    aperto un major, non aggiungiamo un minor automatico sopra."""
    if control_instance is None:
        return False
    return AuditFinding.objects.filter(
        audit_prep=audit_prep,
        control_instance=control_instance,
        status__in=["open", "in_response"],
        deleted_at__isnull=True,
    ).exists()


def auto_validate_prep(prep: AuditPrep, user) -> dict:
    """
    Esegue la validazione automatica su tutti gli EvidenceItem del prep.
    Aggiorna gli stati e apre i finding per gli item `mancante`/`scaduto`.
    Restituisce un summary numerico per la UI.
    """
    today = timezone.now().date()
    audit_date = prep.audit_date or today

    counters = {
        "evaluated": 0,
        "presente": 0,
        "scaduto": 0,
        "mancante": 0,
        "findings_created": 0,
        "findings_skipped_existing": 0,
    }

    items = list(
        prep.evidence_items
        .filter(deleted_at__isnull=True)
        .select_related("control_instance__control")
    )

    with transaction.atomic():
        for item in items:
            new_status, reasons = _evaluate_evidence_item(item)
            counters["evaluated"] += 1
            counters[new_status] += 1

            updates: list[str] = []
            if item.status != new_status:
                item.status = new_status
                updates.append("status")
            # Annota l'esito nelle note (sostituisce la riga "Auto:" precedente).
            note_marker = "[Auto-validate"
            kept_lines = [
                ln for ln in (item.notes or "").splitlines()
                if not ln.startswith(note_marker)
            ]
            kept_lines.append(
                f"{note_marker} {today.isoformat()}] {new_status}: " + "; ".join(reasons)
            )
            item.notes = "\n".join(kept_lines)
            updates.append("notes")
            updates.append("updated_at")
            item.save(update_fields=updates)

            if new_status in ("mancante", "scaduto"):
                if _has_open_finding(item.control_instance, prep):
                    counters["findings_skipped_existing"] += 1
                    continue

                ci = item.control_instance
                title_subject = (
                    f"{ci.control.external_id}" if ci and getattr(ci, "control", None)
                    else item.description[:80]
                )
                if new_status == "mancante":
                    finding_title = f"Evidenza mancante — {title_subject}"
                else:
                    finding_title = f"Evidenza scaduta — {title_subject}"

                description = (
                    f"Generato automaticamente dalla validazione del "
                    f"{today.isoformat()}.\n"
                    f"Control: {title_subject}\n"
                    f"Esito: {new_status}\n"
                    f"Motivi: " + "; ".join(reasons)
                )

                open_finding(
                    audit_prep=prep,
                    finding_type="minor_nc",
                    title=finding_title,
                    description=description,
                    audit_date=audit_date,
                    user=user,
                    control_instance=ci,
                    auditor_name=prep.auditor_name or "Auto-validation",
                    auto_generated=True,
                )
                counters["findings_created"] += 1

        # Aggiorna il readiness score in base ai nuovi stati.
        update_readiness_score(prep)
        counters["readiness_score"] = prep.readiness_score or 0

        warning = _detect_missing_extended_frameworks(prep)
        if warning:
            counters["warning"] = warning

        log_action(
            user=user,
            action_code="audit_prep.auto_validation.run",
            level="L2",
            entity=prep,
            payload={
                "title": prep.title,
                **{k: v for k, v in counters.items() if k != "warning"},
                "warning_code": warning["code"] if warning else None,
            },
        )

    return counters
