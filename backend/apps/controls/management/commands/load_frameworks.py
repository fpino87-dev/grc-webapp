import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction


def _merge_translations(existing: dict, incoming: dict) -> dict:
    """Merge per-lingua: i campi del file JSON sovrascrivono, ma chiavi extra
    presenti nel DB (es. `practical_summary` generato dall'AI) vengono preservate.
    """
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(incoming, dict):
        return existing
    out: dict = {}
    langs = set(existing.keys()) | set(incoming.keys())
    for lang in langs:
        ex = existing.get(lang) or {}
        inc = incoming.get(lang) or {}
        if not isinstance(ex, dict):
            ex = {}
        if not isinstance(inc, dict):
            inc = {}
        out[lang] = {**ex, **inc}
    return out


class Command(BaseCommand):
    help = "Importa framework normativi da backend/frameworks/*.json"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        from apps.controls.models import Control, ControlDomain, ControlMapping, Framework

        base = Path(__file__).resolve().parents[4] / "frameworks"
        files = [Path(options["file"])] if options["file"] else sorted(base.glob("*.json"))
        if not files:
            self.stdout.write(self.style.WARNING("Nessun JSON in backend/frameworks/"))
            return
        for fp in files:
            data = json.loads(fp.read_text("utf-8"))
            self.stdout.write(f"→ {fp.name}")
            if options["dry_run"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [DRY-RUN] {len(data.get('controls', []))} controlli",
                    )
                )
                continue
            with transaction.atomic():
                fw, _ = Framework.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "name": data["name"],
                        "version": data["version"],
                        "published_at": data["published_at"],
                    },
                )
                dm: dict[str, ControlDomain] = {}
                for d in data.get("domains", []):
                    existing = ControlDomain.objects.filter(
                        framework=fw, code=d["code"]
                    ).first()
                    merged_tr = _merge_translations(
                        existing.translations if existing else {},
                        d["translations"],
                    )
                    obj, _ = ControlDomain.objects.update_or_create(
                        framework=fw,
                        code=d["code"],
                        defaults={
                            "translations": merged_tr,
                            "order": d.get("order", 0),
                        },
                    )
                    dm[d["code"]] = obj
                cm: dict[str, Control] = {}
                for c in data.get("controls", []):
                    existing = Control.objects.filter(
                        framework=fw, external_id=c["external_id"]
                    ).first()
                    merged_tr = _merge_translations(
                        existing.translations if existing else {},
                        c["translations"],
                    )
                    obj, _ = Control.objects.update_or_create(
                        framework=fw,
                        external_id=c["external_id"],
                        defaults={
                            "domain": dm.get(c.get("domain")),
                            "translations": merged_tr,
                            "level": c.get("level", ""),
                            "evidence_requirement": c.get("evidence_requirement", {}),
                            "control_category": c.get("control_category", "procedurale"),
                        },
                    )
                    cm[c["external_id"]] = obj
                for m in data.get("mappings", []):
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
            self.stdout.write(self.style.SUCCESS(f"  OK — {len(cm)} controlli"))

