"""
Management command: python manage.py cleanup_orphan_control_instances

Trova e (opzionalmente) soft-deleta le `ControlInstance` "orfane" — istanze
collegate a un framework che non e' (piu') assegnato al loro plant via
`PlantFramework`.

Tipiche cause:
- riassegnazione di framework prima del fix S10 (hard-delete del PlantFramework
  che non cascade-cancellava le ControlInstance);
- seed/fixture iniziali che hanno creato ControlInstance senza creare
  PlantFramework gemello.

Effetto operativo: queste istanze sono **invisibili** nella vista controlli
(che filtra per `get_active_frameworks(plant)`) ma esistono nel DB con tutto
il loro storico (status, owner, documenti collegati, note).

Prima di soft-deletare, il comando salva uno **snapshot CSV** in
`/app/exports/cleanup_orphan_<plant_code>_<framework>_<YYYY-MM-DD>.csv`
con tutti i dati delle istanze rimosse — e' la fonte di verita' per
ricostruire le valutazioni se serve.

Uso:
    # Dry-run (default): elenca le orfane e genera il CSV, NON cancella
    python manage.py cleanup_orphan_control_instances --plant IT-ITA

    # Filtra per framework specifico
    python manage.py cleanup_orphan_control_instances --plant IT-ITA --framework NIS2

    # Applica davvero il soft-delete (richiede --confirm e --user)
    python manage.py cleanup_orphan_control_instances \\
        --plant IT-ITA --framework NIS2 --apply --user admin@azienda.it
"""
from __future__ import annotations

import csv
import os
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Trova ControlInstance orfane (framework non assegnato al plant via "
        "PlantFramework), salva snapshot CSV ed eventualmente soft-deleta."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--plant", required=True,
            help="Codice del plant (es. IT-ITA)",
        )
        parser.add_argument(
            "--framework",
            help="Codice framework specifico (es. NIS2). Se omesso analizza tutti i framework con istanze orfane.",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help="Esegue il soft-delete. Senza questo flag e' dry-run (solo CSV).",
        )
        parser.add_argument(
            "--user",
            help="Email dell'utente che firma l'operazione nell'audit log (richiesto con --apply).",
        )
        parser.add_argument(
            "--reason",
            default="cleanup orfani — framework non assegnato al plant",
            help="Motivo del soft-delete (finisce nell'audit log payload).",
        )
        parser.add_argument(
            "--export-dir", default="/app/exports",
            help="Directory dove salvare il CSV (default: /app/exports).",
        )

    def handle(self, *args, **options):
        from apps.controls.models import ControlInstance, Framework
        from apps.plants.models import Plant, PlantFramework
        from core.audit import log_action

        User = get_user_model()

        plant_code = options["plant"]
        framework_code = options.get("framework")
        apply_changes = options["apply"]
        user_email = options.get("user")
        reason = options["reason"]
        export_dir = options["export_dir"]

        try:
            plant = Plant.objects.get(code=plant_code, deleted_at__isnull=True)
        except Plant.DoesNotExist as exc:
            raise CommandError(f"Plant '{plant_code}' non trovato.") from exc

        active_fw_ids = list(
            PlantFramework.objects.filter(
                plant=plant, deleted_at__isnull=True, active=True,
            ).values_list("framework_id", flat=True)
        )

        orphans_qs = ControlInstance.objects.filter(
            plant=plant,
            deleted_at__isnull=True,
        ).exclude(control__framework_id__in=active_fw_ids).select_related(
            "control", "control__framework", "owner",
        )

        if framework_code:
            try:
                target_fw = Framework.objects.get(code=framework_code)
            except Framework.DoesNotExist as exc:
                raise CommandError(f"Framework '{framework_code}' non trovato.") from exc
            orphans_qs = orphans_qs.filter(control__framework=target_fw)

        orphans = list(orphans_qs.order_by("control__framework__code", "control__external_id"))
        if not orphans:
            self.stdout.write(self.style.SUCCESS(
                f"Nessuna ControlInstance orfana per plant={plant_code}"
                + (f", framework={framework_code}" if framework_code else "")
            ))
            return

        # Snapshot CSV (sempre, dry-run o apply)
        os.makedirs(export_dir, exist_ok=True)
        today = date.today().isoformat()
        fw_label = framework_code or "all"
        csv_path = os.path.join(
            export_dir,
            f"cleanup_orphan_{plant_code}_{fw_label}_{today}.csv",
        )

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "framework_code", "external_id", "title_it", "description_it",
                "status", "owner_email", "last_evaluated_at",
                "notes", "doc_count", "doc_titles",
            ])
            for ci in orphans:
                docs = list(ci.documents.filter(deleted_at__isnull=True).values("id", "title", "status"))
                title_it = ci.control.get_title("it")
                trans = ci.control.translations or {}
                desc_it = (trans.get("it") or {}).get("description", "") or (trans.get("en") or {}).get("description", "")
                writer.writerow([
                    ci.control.framework.code if ci.control.framework_id else "",
                    ci.control.external_id,
                    title_it,
                    desc_it,
                    ci.status,
                    ci.owner.email if ci.owner_id else "",
                    ci.last_evaluated_at.isoformat() if ci.last_evaluated_at else "",
                    (ci.notes or "").replace("\n", " | "),
                    len(docs),
                    " | ".join(f"[{d['status']}] {d['title']}" for d in docs),
                ])

        self.stdout.write(self.style.SUCCESS(
            f"Snapshot CSV salvato: {csv_path} ({len(orphans)} righe)"
        ))

        # Riepilogo
        from collections import Counter
        by_fw = Counter(ci.control.framework.code if ci.control.framework_id else "NO_FW" for ci in orphans)
        self.stdout.write(f"\nControlInstance orfane su plant {plant_code}:")
        for fw, n in by_fw.items():
            self.stdout.write(f"  {fw}: {n}")
        by_status = Counter(ci.status for ci in orphans)
        self.stdout.write("Status distribution:")
        for st, n in by_status.most_common():
            self.stdout.write(f"  {st}: {n}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN — nessuna modifica al DB. Per applicare: --apply --user <email>"
            ))
            return

        if not user_email:
            raise CommandError("--apply richiede --user <email> per firmare l'audit log.")

        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist as exc:
            raise CommandError(f"Utente '{user_email}' non trovato.") from exc

        now = timezone.now()
        with transaction.atomic():
            for ci in orphans:
                ci.deleted_at = now
                ci.save(update_fields=["deleted_at", "updated_at"])
                log_action(
                    user=user,
                    action_code="controls.instance.cleanup_orphan",
                    level="L1",
                    entity=ci,
                    payload={
                        "plant_code": plant_code,
                        "framework_code": ci.control.framework.code if ci.control.framework_id else "",
                        "external_id": ci.control.external_id,
                        "previous_status": ci.status,
                        "reason": reason,
                        "snapshot_csv": csv_path,
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Soft-deletate {len(orphans)} ControlInstance orfane. "
            f"Audit log: 'controls.instance.cleanup_orphan' (level L1) firmato da {user_email}."
        ))
