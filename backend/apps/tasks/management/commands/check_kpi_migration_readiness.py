"""Pre-flight per la migrazione tasks.0009 (kpi_code unico per sito).

Da lanciare in produzione PRIMA di `migrate`. Non modifica nulla: verifica
che i dati esistenti soddisfino i due nuovi vincoli e riepiloga cosa
cambiera' dopo la migrazione.

    python manage.py check_kpi_migration_readiness

Exit code 0 = si puo' migrare, 1 = ci sono duplicati da sanare a mano.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verifica che i dati KPI siano compatibili con la migrazione tasks.0009."

    def handle(self, *args, **options):
        from apps.tasks.models import KPIDefinition

        rows = list(
            KPIDefinition.objects.all_with_deleted()
            .select_related("plant")
            .values("kpi_code", "plant_id", "deleted_at", "plant__code")
        )
        active = [r for r in rows if r["deleted_at"] is None]
        deleted = [r for r in rows if r["deleted_at"] is not None]

        self.stdout.write(f"Definizioni KPI totali: {len(rows)}")
        self.stdout.write(f"  attive:              {len(active)}")
        self.stdout.write(f"  cancellate (logico): {len(deleted)}")

        # I due vincoli che la migrazione sta per creare.
        per_plant = Counter(
            (r["kpi_code"], r["plant_id"]) for r in active if r["plant_id"] is not None
        )
        globali = Counter(r["kpi_code"] for r in active if r["plant_id"] is None)
        dup_plant = {k: n for k, n in per_plant.items() if n > 1}
        dup_global = {k: n for k, n in globali.items() if n > 1}

        ok = True
        if dup_plant:
            ok = False
            self.stdout.write(self.style.ERROR(
                "\nBLOCCANTE — stesso kpi_code attivo piu' volte sullo stesso sito:"
            ))
            for (code, _pid), n in sorted(dup_plant.items()):
                self.stdout.write(f"   {code}: {n} righe")
        if dup_global:
            ok = False
            self.stdout.write(self.style.ERROR(
                "\nBLOCCANTE — stesso kpi_code attivo piu' volte come definizione globale:"
            ))
            for code, n in sorted(dup_global.items()):
                self.stdout.write(f"   {code}: {n} righe")

        # Verifica che il vecchio indice globale sia ancora in piedi: e' lui a
        # garantire che i duplicati non possano esistere.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'tasks_kpidefinition' AND indexdef LIKE '%UNIQUE%'"
            )
            indexes = sorted(r[0] for r in cur.fetchall())
        self.stdout.write(f"\nIndici unici presenti ora: {', '.join(indexes) or 'nessuno'}")
        if any("uniq_active_kpi_code" in i for i in indexes):
            self.stdout.write(self.style.WARNING(
                "  La migrazione risulta gia' applicata su questo database."
            ))

        if deleted:
            self.stdout.write(
                "\nDefinizioni cancellate che dopo la migrazione smettono di "
                "occupare il codice (ripristinabili dal wizard «Consiglia KPI», "
                "conservando lo storico):"
            )
            for r in sorted(deleted, key=lambda r: r["kpi_code"]):
                scope = r["plant__code"] or "GLOBALE"
                self.stdout.write(f"   {r['kpi_code']}  [{scope}]")

        if ok:
            self.stdout.write(self.style.SUCCESS(
                "\nOK — nessun duplicato: la migrazione tasks.0009 puo' essere applicata."
            ))
            return
        self.stdout.write(self.style.ERROR(
            "\nSANARE i duplicati elencati prima di lanciare `migrate`."
        ))
        raise SystemExit(1)
