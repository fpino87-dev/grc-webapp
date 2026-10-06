"""Il Plant Manager non accetta più i rischi: non sempre ne risponde e può
avere deleghe limitate. Dove la policy lo chiedeva decide l'organo nel
riesame di direzione (procedura §10).

- Policy salvate (organizzazione e siti): il Plant Manager esce dai ruoli e la
  classe richiede la delibera dell'organo.
- Accettazioni in approvazione senza la firma del Plant Manager: il ruolo
  esce dalle firme richieste e l'accettazione attende l'organo, così compare
  nell'elenco del prossimo riesame. Quelle già firmate dal Plant Manager, e
  quelle attive o chiuse, restano come sono: la decisione è già presa.
"""
from django.db import migrations

ROLE = "plant_manager"


def forward(apps, schema_editor):
    Policy = apps.get_model("risk", "RiskGovernancePolicy")
    Acceptance = apps.get_model("risk", "RiskAcceptance")

    for policy in Policy.objects.all():
        matrix = policy.acceptance_matrix or {}
        changed = False
        for rule in matrix.values():
            if isinstance(rule, dict) and ROLE in (rule.get("roles") or []):
                rule["roles"] = [r for r in rule["roles"] if r != ROLE]
                rule["requires_body"] = True
                changed = True
        if changed:
            policy.acceptance_matrix = matrix
            policy.save(update_fields=["acceptance_matrix"])

    for acc in Acceptance.objects.filter(status="pending"):
        if ROLE not in (acc.required_roles or []):
            continue
        if any(s.get("role") == ROLE for s in acc.signatures or []):
            continue
        acc.required_roles = [r for r in acc.required_roles if r != ROLE]
        acc.requires_body = True
        acc.save(update_fields=["required_roles", "requires_body"])


class Migration(migrations.Migration):

    dependencies = [
        ("risk", "0024_riskacceptance_review"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
