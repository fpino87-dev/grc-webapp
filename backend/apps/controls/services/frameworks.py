# ---------------------------------------------------------------------------
# Framework governance (import/preview) — source of truth: backend/frameworks/*.json
# ---------------------------------------------------------------------------

from ..models import Control


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

    from django.conf import settings
    from django.db import transaction
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from ..models import ControlDomain, ControlMapping, Framework

    _validate_framework_payload(data)

    code = data["code"]
    version = data.get("version", "")

    # Persist JSON to disk (single source of truth)
    if overwrite_json_file:
        # BASE_DIR = backend/ — stessa cartella usata da load_frameworks
        base = Path(settings.BASE_DIR) / "frameworks"
        base.mkdir(parents=True, exist_ok=True)
        fp = base / f"{code}.json"
        fp.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        fp = None

    with transaction.atomic():
        # NB: non spacchettare in `_`: shadowerebbe gettext (usato nel return)
        fw, _created = Framework.objects.update_or_create(
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
            obj, _created = ControlDomain.objects.update_or_create(
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
            obj, _created = Control.objects.update_or_create(
                framework=fw,
                external_id=c["external_id"],
                defaults={
                    "domain": dm.get(c.get("domain")),
                    "translations": c["translations"],
                    "level": c.get("level", ""),
                    "evidence_requirement": c.get("evidence_requirement", {}),
                    "control_category": c.get("control_category", "procedurale"),
                    "requirements": c.get("requirements", []),
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

    from ..models import Framework, ControlDomain

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

    framework.archived_at = timezone.localdate()
    framework.save(update_fields=["archived_at", "updated_at"])

    log_action(
        user=user,
        action_code="controls.framework.archive",
        level="L1",
        entity=framework,
        payload={"id": str(framework.id), "code": framework.code},
    )
