from .models import Control, ControlInstance


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


def check_evidence_requirements(instance, lang: str | None = None) -> dict:
    """
    Verifica se ControlInstance soddisfa i requisiti definiti
    in Control.evidence_requirement.
    """
    from django.utils import timezone
    from django.utils import translation
    from django.utils.translation import gettext as _

    if lang is None:
        lang = translation.get_language() or "it"

    today = timezone.now().date()
    req = instance.control.evidence_requirement or {}
    result = {
        "satisfied": True,
        "missing_documents": [],
        "missing_evidences": [],
        "expired_evidences": [],
        "warnings": [],
    }

    # Controlla documenti richiesti
    for doc_req in req.get("documents", []):
        if not doc_req.get("mandatory"):
            continue
        doc_type = doc_req.get("type")
        # Check tipo esatto
        exists_exact = instance.documents.filter(
            document_type=doc_type,
            status="approvato",
            deleted_at__isnull=True,
        ).exists()
        if exists_exact:
            continue
        # Fallback: qualsiasi documento approvato collegato soddisfa il requisito
        # (il tipo è un suggerimento, non un vincolo rigido)
        exists_any = instance.documents.filter(
            status="approvato",
            deleted_at__isnull=True,
        ).exists()
        if exists_any:
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

        ev_qs = list(instance.evidences.filter(
            evidence_type=ev_type,
            deleted_at__isnull=True,
        ))
        if not ev_qs:
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": ev_type,
                "description": description,
            })
            continue

        # Separa evidenze valide da scadute
        valid_evs = [ev for ev in ev_qs if not ev.valid_until or ev.valid_until >= today]
        expired_evs = [ev for ev in ev_qs if ev.valid_until and ev.valid_until < today]

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
    if min_docs > 0:
        count = instance.documents.filter(
            status="approvato", deleted_at__isnull=True
        ).count()
        if count < min_docs:
            result["satisfied"] = False
            result["missing_documents"].append({
                "type": "any",
                "description": _("Richiesti almeno %(count)s documenti approvati") % {"count": min_docs},
            })
    if min_evs > 0:
        count = instance.evidences.filter(
            valid_until__gte=today, deleted_at__isnull=True
        ).count()
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
    falsi gap nel GRC Assistant quando l'evidenza e' caricata sul livello
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

    today = today or timezone.now().date()
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


def evaluate_control(instance, new_status, user, note=""):
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if new_status in ("compliant", "parziale"):
        req_check = check_evidence_requirements(instance)

        if new_status == "compliant" and not req_check["satisfied"]:
            msgs = []
            for md in req_check["missing_documents"]:
                msgs.append(_("• Documento mancante: %(desc)s") % {"desc": md["description"] or md["type"]})
            for me in req_check["missing_evidences"]:
                msgs.append(_("• Evidenza mancante: %(desc)s") % {"desc": me["description"] or me["type"]})
            for ee in req_check["expired_evidences"]:
                msgs.append(
                    _("• Evidenza scaduta: %(title)s (scaduta il %(date)s)") % {
                        "title": ee["title"],
                        "date": ee["expired_on"],
                    }
                )
            # Fallback: if no evidence_requirement defined, require at least one valid evidence
            if not msgs:
                today = timezone.now().date()
                if not instance.evidences.filter(valid_until__gte=today, deleted_at__isnull=True).exists():
                    raise ValidationError(
                        _("Impossibile impostare lo stato a 'compliant' senza almeno un'evidenza valida collegata.")
                    )
            else:
                raise ValidationError(
                    _("Requisiti non soddisfatti per stato Compliant:\n") + "\n".join(msgs)
                )

        if new_status == "parziale":
            today = timezone.now().date()
            has_any = (
                instance.evidences.filter(
                    valid_until__gte=today, deleted_at__isnull=True
                ).exists()
                or instance.documents.filter(
                    status="approvato", deleted_at__isnull=True
                ).exists()
            )
            if not has_any:
                raise ValidationError(
                    _("Almeno un documento approvato o un'evidenza valida richiesti per stato Parziale.")
                )

    if new_status == "na":
        if not note or len(note.strip()) < 20:
            raise ValidationError(
                _("Lo stato N/A richiede una giustificazione scritta di almeno 20 caratteri.")
            )

    instance.status = new_status
    instance.last_evaluated_at = timezone.now()
    instance.last_evaluated_note = note
    update_fields = ["status", "last_evaluated_at", "last_evaluated_note", "updated_at"]
    if new_status == "na":
        instance.na_justification = note
        update_fields.append("na_justification")
    instance.save(update_fields=update_fields)

    log_action(
        user=user,
        action_code="control.evaluated",
        level="L2",
        entity=instance,
        payload={
            "new_status": new_status,
            "note": note,
            "evidences_count": instance.evidences.count(),
            "documents_count": instance.documents.count(),
        },
    )
    return instance


def validate_exclusion(instance, applicability: str,
                       justification: str, user) -> None:
    """
    Valida e applica una modifica di applicabilità.
    Se escluso: richiede giustificazione di almeno 50 caratteri.
    Aggiorna status a 'na' se escluso.
    """
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if applicability == "escluso":
        if not justification or len(justification.strip()) < 50:
            raise ValidationError(
                _("La giustificazione di esclusione per SOA richiede almeno 50 caratteri. Specificare il motivo formale per cui il controllo non è applicabile.")
            )

    instance.applicability = applicability
    instance.exclusion_justification = justification
    if applicability == "escluso":
        instance.status = "na"
        instance.na_justification = justification
    instance.save(update_fields=[
        "applicability", "exclusion_justification",
        "status", "na_justification", "updated_at",
    ])

    log_action(
        user=user,
        action_code="control.applicability_changed",
        level="L2",
        entity=instance,
        payload={
            "applicability": applicability,
            "justification": justification[:100],
        },
    )


def calc_suggested_status(instance) -> str:
    """
    Inferisce lo stato suggerito in base ai documenti/evidenze collegati.
    Regole:
      - Nessun requisito definito → non_valutato
      - Tutti i requisiti soddisfatti → compliant
      - Qualcosa presente (anche scaduto) → parziale
      - Nessuna documentazione → gap
    """
    req = instance.control.evidence_requirement or {}
    has_req = bool(
        req.get("documents") or req.get("evidences")
        or req.get("min_documents") or req.get("min_evidences")
    )
    if not has_req:
        return "non_valutato"

    check = check_evidence_requirements(instance)
    if check["satisfied"]:
        return "compliant"

    has_docs = instance.documents.filter(status="approvato", deleted_at__isnull=True).exists()
    has_ev = instance.evidences.filter(deleted_at__isnull=True).exists()
    if has_docs or has_ev:
        return "parziale"
    return "gap"


# ---------------------------------------------------------------------------
# Framework governance (import/preview) — source of truth: backend/frameworks/*.json
# ---------------------------------------------------------------------------


def _validate_framework_payload(data: dict) -> None:
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    required_top = ["code", "name", "version", "published_at", "controls"]
    missing = [k for k in required_top if k not in data]
    if missing:
        raise ValidationError(
            _("Framework JSON non valido: campi mancanti: %(fields)s")
            % {"fields": ", ".join(missing)}
        )
    if not isinstance(data.get("controls"), list):
        raise ValidationError(_("Framework JSON non valido: 'controls' deve essere una lista."))

    for c in data.get("controls", []):
        if not isinstance(c, dict):
            raise ValidationError(_("Framework JSON non valido: ogni control deve essere un oggetto."))
        for k in ("external_id", "translations"):
            if k not in c:
                raise ValidationError(
                    _("Framework JSON non valido: control senza campo '%(field)s'.")
                    % {"field": k}
                )


def preview_framework_import(data: dict) -> dict:
    """
    Ritorna una preview (no scritture) per l'import di un framework JSON.
    """
    import hashlib
    import json as _json

    _validate_framework_payload(data)

    raw = _json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    sha256 = hashlib.sha256(raw).hexdigest()

    # Determine languages present in payload
    langs: set[str] = set()
    for d in data.get("domains", []):
        tr = (d or {}).get("translations") or {}
        if isinstance(tr, dict):
            langs |= set(tr.keys())
    for c in data.get("controls", []):
        tr = (c or {}).get("translations") or {}
        if isinstance(tr, dict):
            langs |= set(tr.keys())

    return {
        "sha256": sha256,
        "framework": {
            "code": data.get("code"),
            "name": data.get("name"),
            "version": data.get("version"),
            "published_at": data.get("published_at"),
        },
        "counts": {
            "domains": len(data.get("domains", []) or []),
            "controls": len(data.get("controls", []) or []),
            "mappings": len(data.get("mappings", []) or []),
        },
        "languages": sorted(langs),
    }


def import_framework_payload(data: dict, user, *, overwrite_json_file: bool = True) -> dict:
    """
    Importa il framework:
    - (opzionale) salva/aggiorna il JSON in backend/frameworks/<code>.json
    - upsert su DB (Framework, ControlDomain, Control, ControlMapping)
    - audit log
    """
    import json as _json
    from pathlib import Path

    from django.db import transaction
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from .models import Control, ControlDomain, ControlMapping, Framework

    _validate_framework_payload(data)

    code = data["code"]
    version = data.get("version", "")

    # Persist JSON to disk (single source of truth)
    if overwrite_json_file:
        base = Path(__file__).resolve().parents[3] / "frameworks"
        base.mkdir(parents=True, exist_ok=True)
        fp = base / f"{code}.json"
        fp.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        fp = None

    with transaction.atomic():
        fw, _ = Framework.objects.update_or_create(
            code=code,
            defaults={
                "name": data["name"],
                "version": data["version"],
                "published_at": data["published_at"],
                "archived_at": data.get("archived_at"),
            },
        )

        dm: dict[str, ControlDomain] = {}
        for d in data.get("domains", []) or []:
            obj, _ = ControlDomain.objects.update_or_create(
                framework=fw,
                code=d["code"],
                defaults={
                    "translations": d["translations"],
                    "order": d.get("order", 0),
                },
            )
            dm[d["code"]] = obj

        cm: dict[str, Control] = {}
        for c in data.get("controls", []) or []:
            obj, _ = Control.objects.update_or_create(
                framework=fw,
                external_id=c["external_id"],
                defaults={
                    "domain": dm.get(c.get("domain")),
                    "translations": c["translations"],
                    "level": c.get("level", ""),
                    "evidence_requirement": c.get("evidence_requirement", {}),
                    "control_category": c.get("control_category", "procedurale"),
                },
            )
            cm[c["external_id"]] = obj

        # mappings (cross framework)
        mappings_created = 0
        for m in data.get("mappings", []) or []:
            tfw = Framework.objects.filter(code=m.get("target_framework")).first()
            tgt = (
                Control.objects.filter(framework=tfw, external_id=m["target"]).first()
                if tfw
                else None
            )
            src = cm.get(m["source"])
            if src and tgt:
                ControlMapping.objects.update_or_create(
                    source_control=src,
                    target_control=tgt,
                    defaults={"relationship": m["relationship"]},
                )
                mappings_created += 1

    log_action(
        user=user,
        action_code="controls.framework.imported",
        level="L1",
        entity=fw,
        payload={
            "framework_code": code,
            "version": version,
            "file": str(fp) if fp else None,
            "domains": len(dm),
            "controls": len(cm),
            "mappings_upserted": mappings_created,
        },
    )

    return {
        "ok": True,
        "framework": {"id": str(fw.id), "code": fw.code, "name": fw.name, "version": fw.version},
        "message": _("Framework '%(code)s' importato (v%(version)s).")
        % {"code": fw.code, "version": fw.version},
    }


def list_framework_governance_metadata() -> list[dict]:
    """
    Lista framework con metadata utili per Governance UI.
    """
    from django.db.models import Count

    from .models import Framework, Control, ControlDomain

    frameworks = list(
        Framework.objects.all()
        .annotate(controls_count=Count("controls", distinct=True))
        .order_by("code")
        .values("id", "code", "name", "version", "published_at", "archived_at", "controls_count")
    )

    # attach domains_count + languages (best-effort)
    by_code = {f["code"]: f for f in frameworks}
    domain_counts = (
        ControlDomain.objects.values("framework__code")
        .annotate(n=Count("id"))
        .values_list("framework__code", "n")
    )
    for code, n in domain_counts:
        if code in by_code:
            by_code[code]["domains_count"] = n

    # languages: look at a small sample of controls/domains per framework
    for f in frameworks:
        code = f["code"]
        langs: set[str] = set()
        c = (
            Control.objects.filter(framework__code=code)
            .only("translations")
            .first()
        )
        if c and isinstance(c.translations, dict):
            langs |= set(c.translations.keys())
        d = (
            ControlDomain.objects.filter(framework__code=code)
            .only("translations")
            .first()
        )
        if d and isinstance(d.translations, dict):
            langs |= set(d.translations.keys())
        f["languages"] = sorted(langs)
        f["domains_count"] = f.get("domains_count", 0)

    return frameworks

    check = check_evidence_requirements(instance)
    if check["satisfied"]:
        return "compliant"

    has_docs = instance.documents.filter(status="approvato", deleted_at__isnull=True).exists()
    has_ev = instance.evidences.filter(deleted_at__isnull=True).exists()
    if has_docs or has_ev:
        return "parziale"

    return "gap"


def gap_analysis(source_framework_code: str, target_framework_code: str, plant_id, lang: str | None = None) -> dict:
    """
    Confronta due framework e mostra cosa manca per passare dall'uno all'altro.
    """
    from .models import Control, ControlInstance, ControlMapping

    target_controls = Control.objects.filter(
        framework__code=target_framework_code,
        deleted_at__isnull=True,
    ).prefetch_related("mappings_to__source_control")

    result = {
        "source_framework": source_framework_code,
        "target_framework": target_framework_code,
        "covered":    [],
        "partial":    [],
        "gap":        [],
        "not_mapped": [],
        "summary":    {},
    }

    for tc in target_controls:
        mappings = tc.mappings_to.filter(
            source_control__framework__code=source_framework_code
        )
        if not mappings.exists():
            result["not_mapped"].append({
                "id": str(tc.pk),
                "external_id": tc.external_id,
                "title": tc.get_title(lang or "it"),
                "domain": tc.domain.get_name(lang or "it") if tc.domain else "",
            })
            continue

        best_status = "non_valutato"
        for mapping in mappings:
            try:
                ci = ControlInstance.objects.get(
                    plant_id=plant_id,
                    control=mapping.source_control,
                )
                order = {"compliant": 4, "parziale": 3, "na": 2, "gap": 1, "non_valutato": 0}
                if order.get(ci.status, 0) > order.get(best_status, 0):
                    best_status = ci.status
            except ControlInstance.DoesNotExist:
                pass

        entry = {
            "id": str(tc.pk),
            "external_id": tc.external_id,
            "title": tc.get_title(lang or "it"),
            "domain": tc.domain.get_name(lang or "it") if tc.domain else "",
            "source_status": best_status,
        }
        if best_status == "compliant":
            result["covered"].append(entry)
        elif best_status == "parziale":
            result["partial"].append(entry)
        else:
            result["gap"].append(entry)

    total = target_controls.count()
    result["summary"] = {
        "total":      total,
        "covered":    len(result["covered"]),
        "partial":    len(result["partial"]),
        "gap":        len(result["gap"]),
        "not_mapped": len(result["not_mapped"]),
        "pct_ready":  round(len(result["covered"]) / total * 100, 1) if total else 0,
    }
    return result


def get_compliance_summary(plant_id, framework_code=None):
    """
    % di compliance del plant (per framework specifico o globale sui framework
    attivi).

    Regole:
    - I controlli `na` (Non Applicabile) sono fuori contesto organizzativo e
      vengono **esclusi dal denominatore** (non sono ne' gap ne' compliant —
      non li valutiamo affatto).
    - I controlli non-compliant ma coperti da un extender (es. TISAX L2 con
      evidenza caricata sul corrispondente L3 via `ControlMapping(extends)`)
      vengono conteggiati come compliant nel numeratore (la regola di
      copertura e' la stessa di `audit_prep.validation` / `is_covered_by_extender`).

    I campi `compliant_direct` e `covered_by_extender` sono esposti
    separatamente per UI esplicative (es. "29 + 12 coperti da L3").
    """
    from django.db.models import Count
    from django.utils import timezone

    from apps.plants.models import Plant
    from apps.plants.services import get_active_frameworks

    qs = ControlInstance.objects.filter(
        plant_id=plant_id,
        deleted_at__isnull=True,
    )
    if framework_code:
        qs = qs.filter(control__framework__code=framework_code)
    else:
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        active_fws = get_active_frameworks(plant)
        qs = qs.filter(control__framework__in=active_fws)

    na_count = qs.filter(status="na").count()
    qs = qs.exclude(status="na")
    total = qs.count()

    if total == 0:
        return {
            "total": 0,
            "compliant": 0,
            "compliant_direct": 0,
            "covered_by_extender": 0,
            "gap": 0,
            "parziale": 0,
            "non_valutato": 0,
            "na_excluded": na_count,
            "pct_compliant": 0,
        }

    counts = qs.values("status").annotate(n=Count("id"))
    result = {r["status"]: r["n"] for r in counts}
    compliant_direct = result.get("compliant", 0)

    # Conta i non-compliant coperti da un extender (es. TISAX L2 coperto da L3).
    today = timezone.now().date()
    non_compliant_qs = qs.exclude(status="compliant").select_related("control")
    covered_by_extender = 0
    for ci in non_compliant_qs:
        if is_covered_by_extender(ci, today):
            covered_by_extender += 1

    compliant_effective = compliant_direct + covered_by_extender
    return {
        "total": total,
        "compliant": compliant_effective,
        "compliant_direct": compliant_direct,
        "covered_by_extender": covered_by_extender,
        "gap": result.get("gap", 0),
        "parziale": result.get("parziale", 0),
        "non_valutato": result.get("non_valutato", 0),
        "na_excluded": na_count,
        "pct_compliant": round(compliant_effective / total * 100, 1),
    }


def delete_control_instance(instance, user) -> None:
    """
    Soft delete di un'istanza controllo per plant.
    Consentita solo se lo stato è ancora «non_valutato», salvo superuser.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if instance.status != "non_valutato" and not getattr(user, "is_superuser", False):
        raise ValidationError(
            _("Eliminazione consentita solo per controlli non ancora valutati.")
        )

    instance.documents.clear()
    instance.evidences.clear()
    instance.soft_delete()

    log_action(
        user=user,
        action_code="controls.instance.delete",
        level="L2",
        entity=instance,
        payload={
            "id": str(instance.id),
            "plant_id": str(instance.plant_id),
            "control_id": str(instance.control_id),
            "framework": instance.control.framework.code,
            "external_id": instance.control.external_id,
        },
    )


def delete_framework(framework, user) -> None:
    """
    Elimina definitivamente (soft delete) un framework normativo.
    Bloccato se assegnato ad almeno un sito attivo.
    Solo superuser.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from apps.plants.models import PlantFramework
    from core.audit import log_action

    if not getattr(user, "is_superuser", False):
        raise ValidationError(_("Solo il superuser può eliminare un framework."))

    assigned = PlantFramework.objects.filter(
        framework=framework,
        deleted_at__isnull=True,
        plant__deleted_at__isnull=True,
    ).exists()
    if assigned:
        raise ValidationError(
            _("Impossibile eliminare: il framework è ancora assegnato a uno o più siti.")
        )

    log_action(
        user=user,
        action_code="controls.framework.delete",
        level="L1",
        entity=framework,
        payload={"id": str(framework.id), "code": framework.code},
    )
    framework.soft_delete()


def archive_framework(framework, user) -> None:
    """
    Archivia un framework normativo (non elimina i dati catalogo).
    Bloccato se assegnato ad almeno un sito.
    """
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _

    from apps.plants.models import PlantFramework
    from core.audit import log_action

    if not getattr(user, "is_superuser", False):
        raise ValidationError(_("Solo il superuser può archiviare un framework."))

    assigned = PlantFramework.objects.filter(
        framework=framework,
        deleted_at__isnull=True,
        plant__deleted_at__isnull=True,
    ).exists()
    if assigned:
        raise ValidationError(
            _("Impossibile archiviare: il framework è ancora assegnato a uno o più siti.")
        )

    framework.archived_at = timezone.now().date()
    framework.save(update_fields=["archived_at", "updated_at"])

    log_action(
        user=user,
        action_code="controls.framework.archive",
        level="L1",
        entity=framework,
        payload={"id": str(framework.id), "code": framework.code},
    )


# ---------------------------------------------------------------------------
# Propagazione cross-framework (e opzionalmente cross-plant)
# ---------------------------------------------------------------------------

_PROPAGABLE_STATUSES = {"compliant", "na"}
# equivalente → bidirezionale; covers → solo sorgente→target
_PROPAGABLE_RELATIONSHIPS = {"equivalente", "covers"}


def propagate_control(instance, user, cross_plant: bool = False) -> dict:
    """
    Propaga lo stato dell'istanza ai controlli mappati rispettando
    tipo di relazione e direzione.

    Regole:
    - Solo stati 'compliant' e 'na' sono propagabili.
    - 'equivalente'  → bidirezionale (A≡B, quindi B≡A)
    - 'covers'       → solo source → target  (A copre B; B non copre A)
    - 'parziale', 'correlato', 'extends' → ignorati (valutazione separata)
    - cross_plant=False → solo stesso plant
    - cross_plant=True  → tutti i plant che hanno un'istanza del controllo target

    Non esegue la validazione delle evidenze: la propagazione copia il dato
    già validato sul controllo sorgente.

    Returns: {"propagated_to": int, "skipped_no_instance": int}
    """
    from core.audit import log_action
    from django.utils import timezone

    if instance.status not in _PROPAGABLE_STATUSES:
        return {"propagated_to": 0, "skipped_no_instance": 0, "blocked": "status_not_propagable"}

    target_control_ids: set = set()

    # source → target: ok per equivalente e covers
    for m in instance.control.mappings_from.filter(relationship__in=_PROPAGABLE_RELATIONSHIPS):
        target_control_ids.add(m.target_control_id)

    # target → source: solo per equivalente (simmetria)
    for m in instance.control.mappings_to.filter(relationship="equivalente"):
        target_control_ids.add(m.source_control_id)

    if not target_control_ids:
        return {"propagated_to": 0, "skipped_no_instance": 0}

    qs = ControlInstance.objects.filter(
        control_id__in=target_control_ids,
        deleted_at__isnull=True,
    )
    if not cross_plant:
        qs = qs.filter(plant=instance.plant)

    note_origin = instance.na_justification or instance.last_evaluated_note or ""
    note_for_target = f"Propagato da {instance.control.external_id}" + (
        f": {note_origin}" if note_origin else ""
    )

    propagated = 0
    skipped = 0

    for target in qs.select_related("control", "plant"):
        if target.pk == instance.pk:
            continue
        target.status = instance.status
        target.last_evaluated_at = timezone.now()
        target.last_evaluated_note = note_for_target
        update_fields = ["status", "last_evaluated_at", "last_evaluated_note", "updated_at"]
        if instance.status == "na":
            target.na_justification = note_for_target
            update_fields.append("na_justification")
        target.save(update_fields=update_fields)

        log_action(
            user=user,
            action_code="control.propagated",
            level="L2",
            entity=target,
            payload={
                "source_instance": str(instance.pk),
                "source_control": instance.control.external_id,
                "source_plant": str(instance.plant_id),
                "propagated_status": instance.status,
                "cross_plant": cross_plant,
            },
        )
        propagated += 1

    return {"propagated_to": propagated, "skipped_no_instance": skipped}


def generate_procedure_document(control, lang: str, user) -> bytes:
    """
    Generates a .docx procedure document for a Control via AI.
    Returns raw bytes of the Word document.
    """
    from apps.ai_engine.router import route
    from .document_generator import markdown_to_docx

    _LANG_NAMES = {
        "it": "italiano",
        "en": "English",
        "fr": "français",
        "pl": "polski",
        "tr": "Türkçe",
    }
    lang_name = _LANG_NAMES.get(lang, "italiano")

    title_loc = control.get_title(lang) or control.get_title("en") or control.external_id
    desc_loc = (
        control.translations.get(lang, {}).get("description")
        or control.translations.get("en", {}).get("description")
        or ""
    )

    prompt = (
        f"Sei un esperto GRC certificato ISO 27001 e NIS2. "
        f"Genera un documento formale di PROCEDURA operativa per il seguente controllo di sicurezza.\n\n"
        f"Framework: {control.framework.code} — {control.framework.name}\n"
        f"Codice controllo: {control.external_id}\n"
        f"Titolo: {title_loc}\n"
        f"Descrizione: {desc_loc}\n\n"
        f"Regole OBBLIGATORIE:\n"
        f"- Basati ESCLUSIVAMENTE sui requisiti reali del framework {control.framework.code}\n"
        f"- NON inventare requisiti normativi non presenti nel controllo\n"
        f"- Per ogni requisito cita la specifica clausola della norma\n"
        f"- Lingua del documento: {lang_name}\n\n"
        f"Struttura obbligatoria (usa heading Markdown ##):\n"
        f"1. Scopo\n"
        f"2. Ambito di applicazione\n"
        f"3. Riferimenti normativi\n"
        f"4. Ruoli e responsabilità\n"
        f"5. Procedura (passo per passo)\n"
        f"6. KPI e metriche di verifica\n"
        f"7. Frequenza di revisione\n\n"
        f"Output: solo Markdown, nessun preambolo, nessuna spiegazione."
    )

    result = route(
        task_type="generate_procedure",
        prompt=prompt,
        user=user,
        entity_id=control.pk,
        module_source="M03",
        sanitize=False,  # dati normativi puri — nessun PII
        max_tokens=4096,
        timeout=300,
    )

    md_text = result["text"]
    doc_title = f"{control.external_id} — {title_loc}"
    return markdown_to_docx(md_text, title=doc_title)
