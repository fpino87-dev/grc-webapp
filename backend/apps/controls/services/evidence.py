from ..models import ControlInstance


def _pick_translation(value, lang: str | None) -> str:
    """
    Supporta evidence_requirement.description come:
    - stringa
    - dict { "it": "...", "en": "...", ... }
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        if lang and value.get(lang):
            return str(value.get(lang))
        # fallback: prefer en, then first available value
        if value.get("en"):
            return str(value.get("en"))
        for v in value.values():
            if v:
                return str(v)
        return ""
    return str(value)


def _linked_documents(instance) -> list:
    """Documenti collegati non soft-deleted, via `.all()`: usa la cache del
    prefetch quando presente (lista, drawer, audit package) — zero query extra."""
    return [d for d in instance.documents.all() if d.deleted_at is None]


def _linked_evidences(instance) -> list:
    """Evidenze collegate non soft-deleted, via `.all()` (vedi `_linked_documents`)."""
    return [e for e in instance.evidences.all() if e.deleted_at is None]


def check_evidence_requirements(instance, lang: str | None = None) -> dict:
    """
    Verifica se ControlInstance soddisfa i requisiti definiti
    in Control.evidence_requirement.

    I filtri girano in Python su `documents.all()`/`evidences.all()` (C2):
    con `prefetch_related` non esegue nessuna query per istanza, senza
    prefetch al massimo due — prima erano 2–6 `.exists()`/`.count()` a
    chiamata, moltiplicati per riga nelle liste.
    """
    from django.utils import timezone
    from django.utils import translation
    from django.utils.translation import gettext as _

    if lang is None:
        lang = translation.get_language() or "it"

    today = timezone.localdate()
    req = instance.control.evidence_requirement or {}
    result = {
        "satisfied": True,
        "missing_documents": [],
        "missing_evidences": [],
        "expired_evidences": [],
        "warnings": [],
    }

    approved_docs = [d for d in _linked_documents(instance) if d.status == "approvato"]
    evidences = _linked_evidences(instance)

    # Controlla documenti richiesti
    for doc_req in req.get("documents", []):
        if not doc_req.get("mandatory"):
            continue
        doc_type = doc_req.get("type")
        # Check tipo esatto
        if any(d.document_type == doc_type for d in approved_docs):
            continue
        # Fallback: qualsiasi documento approvato collegato soddisfa il requisito
        # (il tipo è un suggerimento, non un vincolo rigido)
        if approved_docs:
            result["warnings"].append(
                _("Documento collegato ma non classificato come '%(type)s' — verificare la classificazione") % {"type": doc_type}
            )
            continue
        result["satisfied"] = False
        result["missing_documents"].append({
            "type": doc_type,
            "description": _pick_translation(doc_req.get("description"), lang),
        })

    # Controlla evidenze richieste
    for ev_req in req.get("evidences", []):
        if not ev_req.get("mandatory"):
            continue
        ev_type = ev_req.get("type")
        max_age = ev_req.get("max_age_days")
        description = _pick_translation(ev_req.get("description"), lang)

        ev_list = [ev for ev in evidences if ev.evidence_type == ev_type]
        if not ev_list:
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": ev_type,
                "description": description,
            })
            continue

        # Separa evidenze valide da scadute
        valid_evs = [ev for ev in ev_list if not ev.valid_until or ev.valid_until >= today]
        expired_evs = [ev for ev in ev_list if ev.valid_until and ev.valid_until < today]

        if valid_evs:
            # Requisito soddisfatto — controlla max_age sulle evidenze valide (solo avviso)
            if max_age:
                for ev in valid_evs:
                    if ev.created_at:
                        age = (today - ev.created_at.date()).days
                        if age > max_age:
                            result["warnings"].append(
                                _("Evidenza '%(title)s' ha %(age)s giorni (max consigliato: %(max_age)s gg)") % {
                                    "title": ev.title,
                                    "age": age,
                                    "max_age": max_age,
                                }
                            )
        else:
            # Nessuna evidenza valida: requisito non soddisfatto
            result["satisfied"] = False
            for ev in expired_evs:
                result["expired_evidences"].append({
                    "id": str(ev.id),
                    "title": ev.title,
                    "expired_on": str(ev.valid_until),
                })

    # Controlla minimi
    min_docs = req.get("min_documents", 0)
    min_evs = req.get("min_evidences", 0)
    if min_docs > 0 and len(approved_docs) < min_docs:
        result["satisfied"] = False
        result["missing_documents"].append({
            "type": "any",
            "description": _("Richiesti almeno %(count)s documenti approvati") % {"count": min_docs},
        })
    if min_evs > 0:
        # Come il filtro originale valid_until__gte: le evidenze senza scadenza
        # NON contano per il minimo
        count = sum(1 for ev in evidences if ev.valid_until and ev.valid_until >= today)
        if count < min_evs:
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": "any",
                "description": _("Richieste almeno %(count)s evidenze valide") % {"count": min_evs},
            })

    return result


def get_extender_instances(ci) -> list:
    """
    Restituisce le `ControlInstance` che estendono `ci.control` sullo stesso
    plant via `ControlMapping(relationship="extends")`.

    La direzione e' una sola: chi estende copre l'esteso (es. TISAX L3 estende
    L2 -> evidenza/documento su L3 vale anche per L2). L'inverso non vale.

    Single source of truth: usata sia da `audit_prep.validation` per la
    validazione dell'AuditPrep, sia da `ai_engine.agent_tools` per evitare
    falsi gap nel govrico Assistant quando l'evidenza e' caricata sul livello
    estendente. Modificare la regola qui significa propagarla ovunque.
    """
    extender_control_ids = list(
        ci.control.mappings_to.filter(
            relationship="extends",
        ).values_list("source_control_id", flat=True)
    )
    if not extender_control_ids:
        return []
    return list(
        ControlInstance.objects.filter(
            plant=ci.plant,
            control_id__in=extender_control_ids,
            deleted_at__isnull=True,
        ).select_related("control")
    )


def is_covered_by_extender(ci, today=None) -> bool:
    """
    True se almeno un extender ControlInstance dello stesso plant ha:
    - >= 1 evidenza valida (no expiry o valid_until >= oggi)
    - AND >= 1 documento approvato valido (no expiry o expiry_date >= oggi)

    Stessa semantica di `audit_prep.validation._evaluate_evidence_item` per la
    parte "fonti aggregate": se gli extender sono coperti, copre anche il
    controllo esteso.
    """
    from django.db.models import Q
    from django.utils import timezone

    from apps.documents.models import Document, Evidence

    today = today or timezone.localdate()
    extenders = get_extender_instances(ci)
    if not extenders:
        return False

    extender_ci_ids = [e.pk for e in extenders]

    has_valid_evidence = (
        Evidence.objects.filter(
            control_instances__in=extender_ci_ids,
            deleted_at__isnull=True,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        .exists()
    )
    if not has_valid_evidence:
        return False

    has_valid_doc = (
        Document.objects.filter(
            control_refs__in=extender_ci_ids,
            deleted_at__isnull=True,
            status="approvato",
        )
        .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
        .exists()
    )
    return has_valid_doc


def calc_suggested_status(instance, check: dict | None = None) -> str:
    """
    Inferisce lo stato suggerito in base ai documenti/evidenze collegati.
    Regole:
      - Nessun requisito definito → non_valutato
      - Tutti i requisiti soddisfatti → compliant
      - Qualcosa presente (anche scaduto) → parziale
      - Nessuna documentazione → gap

    `check`: risultato di `check_evidence_requirements` già calcolato dal
    chiamante (es. detail-info del drawer), per non rieseguirlo (C2).
    """
    req = instance.control.evidence_requirement or {}
    has_req = bool(
        req.get("documents") or req.get("evidences")
        or req.get("min_documents") or req.get("min_evidences")
    )
    if not has_req:
        return "non_valutato"

    if check is None:
        check = check_evidence_requirements(instance)
    if check["satisfied"]:
        return "compliant"

    has_docs = any(d.status == "approvato" for d in _linked_documents(instance))
    has_ev = bool(_linked_evidences(instance))
    if has_docs or has_ev:
        return "parziale"
    return "gap"
