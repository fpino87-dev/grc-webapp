from django.core.management.base import BaseCommand

from apps.governance.models import RoleRequirement


# (role, scope_level, applies_to, org_covers_sites, framework_refs)
DEFAULTS = [
    ("ciso", "org", "all", False, ["ISO27001:A.5.2", "NIS2:art.20"]),
    ("isms_manager", "org", "all", False, ["ISO27001:5.3"]),
    ("risk_manager", "org", "all", False, ["ISO27001:6.1"]),
    ("internal_auditor", "org", "all", False, ["ISO27001:9.2"]),
    ("nis2_contact", "plant", "nis2_only", False, ["NIS2:art.23"]),
    ("dpo", "plant", "all", True, ["GDPR:art.37"]),
]


class Command(BaseCommand):
    help = "Carica/aggiorna i requisiti di ruolo di default per la matrice di copertura (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Ripristina applies_to/org_covers_sites/framework_refs/enabled ai default anche se il requisito esiste già.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        created, updated = 0, 0

        for role, scope_level, applies_to, org_covers_sites, refs in DEFAULTS:
            obj = RoleRequirement.objects.filter(
                role=role, scope_level=scope_level, deleted_at__isnull=True,
            ).first()
            if obj is None:
                RoleRequirement.objects.create(
                    role=role,
                    scope_level=scope_level,
                    applies_to=applies_to,
                    org_covers_sites=org_covers_sites,
                    framework_refs=refs,
                    enabled=True,
                )
                created += 1
            elif reset:
                obj.applies_to = applies_to
                obj.org_covers_sites = org_covers_sites
                obj.framework_refs = refs
                obj.enabled = True
                obj.save(update_fields=["applies_to", "org_covers_sites", "framework_refs", "enabled", "updated_at"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Requisiti ruolo: {created} creati, {updated} aggiornati."
        ))
