from django.db import migrations


# (role, scope_level, applies_to, org_covers_sites, framework_refs)
DEFAULTS = [
    ("ciso", "org", "all", False, ["ISO27001:A.5.2", "NIS2:art.20"]),
    ("isms_manager", "org", "all", False, ["ISO27001:5.3"]),
    ("risk_manager", "org", "all", False, ["ISO27001:6.1"]),
    ("internal_auditor", "org", "all", False, ["ISO27001:9.2"]),
    ("nis2_contact", "plant", "nis2_only", False, ["NIS2:art.23"]),
    ("dpo", "plant", "all", True, ["GDPR:art.37"]),
]


def seed(apps, schema_editor):
    RoleRequirement = apps.get_model("governance", "RoleRequirement")
    for role, scope_level, applies_to, org_covers_sites, refs in DEFAULTS:
        exists = RoleRequirement.objects.filter(
            role=role, scope_level=scope_level, deleted_at__isnull=True,
        ).exists()
        if exists:
            continue
        RoleRequirement.objects.create(
            role=role,
            scope_level=scope_level,
            applies_to=applies_to,
            org_covers_sites=org_covers_sites,
            framework_refs=refs,
            enabled=True,
        )


def unseed(apps, schema_editor):
    RoleRequirement = apps.get_model("governance", "RoleRequirement")
    RoleRequirement.objects.filter(
        role__in=[d[0] for d in DEFAULTS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0005_rolerequirement"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
