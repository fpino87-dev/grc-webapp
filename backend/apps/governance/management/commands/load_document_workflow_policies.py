"""Policy di workflow documentale predefinite (M07).

Traducono in configurazione la prassi decisa con la direzione:

- **politiche**: le delibera l'organo di governo in seduta (il CdA), quindi
  l'approvazione in applicazione da parte di un singolo è rifiutata;
- **procedure e manuali**: li approva il CISO o il referente ISMS, e di essi
  l'organo prende atto in riesame di direzione;
- **contratti, NDA e registri**: li chiude il loro titolare;
- su ciò che è obbligatorio vale la **separazione dei compiti**: chi redige non
  chiude la revisione.

Idempotente: aggiorna le policy di organizzazione già presenti e crea quelle
mancanti, senza toccare le policy definite per singolo sito o BU.
"""
from django.core.management.base import BaseCommand

from apps.governance.models import DocumentWorkflowPolicy, NormativeRole, SecurityCommittee

DRAFTERS = [NormativeRole.COMPLIANCE_OFFICER, NormativeRole.ISMS_MANAGER]
REVIEWERS = [NormativeRole.CISO, NormativeRole.COMPLIANCE_OFFICER]

POLICIES = {
    "policy": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO],
        "requires_body_resolution": True,
        "require_distinct_reviewer": True,
        "owner_can_approve": False,
    },
    "procedura": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO, NormativeRole.ISMS_MANAGER],
        "requires_body_resolution": False,
        "require_distinct_reviewer": True,
        "owner_can_approve": False,
    },
    "manuale": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO, NormativeRole.ISMS_MANAGER],
        "requires_body_resolution": False,
        "require_distinct_reviewer": True,
        "owner_can_approve": False,
    },
    "registro": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO, NormativeRole.ISMS_MANAGER],
        "requires_body_resolution": False,
        "require_distinct_reviewer": False,
        "owner_can_approve": True,
    },
    "contratto": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO],
        "requires_body_resolution": False,
        "require_distinct_reviewer": False,
        "owner_can_approve": True,
    },
    "altro": {
        "submit_roles": DRAFTERS,
        "review_roles": REVIEWERS,
        "approve_roles": [NormativeRole.CISO, NormativeRole.ISMS_MANAGER],
        "requires_body_resolution": False,
        "require_distinct_reviewer": False,
        "owner_can_approve": False,
    },
}


class Command(BaseCommand):
    help = "Carica o aggiorna le policy di workflow documentale di organizzazione."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostra le modifiche senza scriverle.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        body = SecurityCommittee.objects.filter(
            committee_type="cda", deleted_at__isnull=True,
        ).order_by("name").first()
        if body is None:
            self.stdout.write(self.style.WARNING(
                "Nessun organo di amministrazione (CdA) definito: le politiche restano "
                "senza organo competente, da indicare al momento della delibera."
            ))

        created = updated = 0
        for document_type, values in POLICIES.items():
            fields = dict(values)
            if fields.get("requires_body_resolution"):
                fields["approval_body"] = body

            policy = DocumentWorkflowPolicy.objects.filter(
                document_type=document_type, scope_type="org", deleted_at__isnull=True,
            ).first()

            if policy is None:
                if not dry_run:
                    DocumentWorkflowPolicy.objects.create(
                        document_type=document_type, scope_type="org", **fields,
                    )
                created += 1
                self.stdout.write(f"  + {document_type}: creata")
                continue

            changes = [
                k for k, v in fields.items()
                if getattr(policy, f"{k}_id" if k == "approval_body" else k)
                != (v.pk if k == "approval_body" and v else v)
            ]
            if not changes:
                self.stdout.write(f"  = {document_type}: già allineata")
                continue
            if not dry_run:
                for k, v in fields.items():
                    setattr(policy, k, v)
                policy.save(update_fields=[*fields.keys(), "updated_at"])
            updated += 1
            self.stdout.write(f"  ~ {document_type}: aggiornata ({', '.join(changes)})")

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Policy di workflow documentale: {created} create, {updated} aggiornate."
        ))
