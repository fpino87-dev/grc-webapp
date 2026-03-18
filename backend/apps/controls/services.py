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
        exists = instance.documents.filter(
            document_type=doc_type,
            status="approvato",
            deleted_at__isnull=True,
        ).exists()
        if not exists:
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

        ev_qs = instance.evidences.filter(
            evidence_type=ev_type,
            deleted_at__isnull=True,
        )
        if not ev_qs.exists():
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": ev_type,
                "description": description,
            })
            continue

        for ev in ev_qs:
            if ev.valid_until and ev.valid_until < today:
                result["expired_evidences"].append({
                    "id": str(ev.id),
                    "title": ev.title,
                    "expired_on": str(ev.valid_until),
                })
                result["satisfied"] = False
            elif max_age and ev.created_at:
                age = (today - ev.created_at.date()).days
                if age > max_age:
                    result["warnings"].append(
                        _("Evidenza '%(title)s' ha %(age)s giorni (max consigliato: %(max_age)s gg)") % {
                            "title": ev.title,
                            "age": age,
                            "max_age": max_age,
                        }
                    )

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
    instance.save(update_fields=[
        "status", "last_evaluated_at", "last_evaluated_note", "updated_at"
    ])

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
    from apps.plants.services import get_active_frameworks
    from apps.plants.models import Plant

    qs = ControlInstance.objects.filter(plant_id=plant_id)
    if framework_code:
        qs = qs.filter(control__framework__code=framework_code)
    else:
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        active_fws = get_active_frameworks(plant)
        qs = qs.filter(control__framework__in=active_fws)
    total = qs.count()
    if total == 0:
        return {"total": 0, "compliant": 0, "gap": 0, "parziale": 0, "na": 0, "non_valutato": 0, "pct_compliant": 0}
    from django.db.models import Count

    counts = qs.values("status").annotate(n=Count("id"))
    result = {r["status"]: r["n"] for r in counts}
    compliant = result.get("compliant", 0)
    return {
        "total": total,
        "compliant": compliant,
        "gap": result.get("gap", 0),
        "parziale": result.get("parziale", 0),
        "na": result.get("na", 0),
        "non_valutato": result.get("non_valutato", 0),
        "pct_compliant": round(compliant / total * 100, 1),
    }
