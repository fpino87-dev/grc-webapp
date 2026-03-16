from django.core.management.base import BaseCommand

from apps.auth_grc.models import RoleCompetencyRequirement


REQUIREMENTS = [
    # (grc_role, competency, required_level, evidence_type, mandatory)

    # CISO
    ("ciso", "ISO 27001 Lead Implementer", 3, "certification", True),
    ("ciso", "NIS2 Compliance", 3, "training", True),
    ("ciso", "Risk Assessment ISO 27005", 2, "training", True),
    ("ciso", "Incident Response", 2, "training", True),

    # Compliance Officer
    ("compliance_officer", "ISO 27001 Lead Implementer", 3, "certification", True),
    ("compliance_officer", "Risk Assessment ISO 27005", 2, "training", True),
    ("compliance_officer", "TISAX Assessment", 2, "training", True),
    ("compliance_officer", "NIS2 Compliance", 2, "training", True),

    # Risk Manager
    ("risk_manager", "Risk Assessment ISO 27005", 3, "certification", True),
    ("risk_manager", "Threat Intelligence", 2, "training", True),
    ("risk_manager", "BIA Methodology", 2, "training", True),

    # Internal Auditor
    ("internal_auditor", "ISO 27001 Lead Auditor", 3, "certification", True),
    ("internal_auditor", "Audit Techniques", 2, "training", True),
    ("internal_auditor", "TISAX Assessment", 2, "training", True),

    # Plant Manager
    ("plant_manager", "Information Security Awareness", 2, "training", True),
    ("plant_manager", "Incident Response", 1, "training", True),

    # Control Owner
    ("control_owner", "Information Security Awareness", 2, "training", True),
    ("control_owner", "Risk Assessment ISO 27005", 1, "training", True),

    # External Auditor
    ("external_auditor", "ISO 27001 Lead Auditor", 3, "certification", True),
    ("external_auditor", "TISAX Assessment", 2, "certification", True),
]


class Command(BaseCommand):
    help = "Carica i requisiti di competenza per ogni ruolo GRC"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Cancella e ricrea tutti i requisiti",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = RoleCompetencyRequirement.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cancellati {deleted} requisiti"))

        created = 0
        existing = 0
        for role, comp, level, ev_type, mandatory in REQUIREMENTS:
            obj, c = RoleCompetencyRequirement.objects.get_or_create(
                grc_role=role,
                competency=comp,
                defaults={
                    "required_level": level,
                    "evidence_type": ev_type,
                    "mandatory": mandatory,
                },
            )
            if c:
                created += 1
            else:
                existing += 1

        self.stdout.write(self.style.SUCCESS(
            f"Completato: {created} creati, {existing} già esistenti. "
            f"Totale: {RoleCompetencyRequirement.objects.count()}"
        ))
