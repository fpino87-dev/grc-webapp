from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0008_remove_duplicate_role_assignments"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="roleassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("valid_until__isnull", True)),
                fields=("user", "role", "scope_type", "scope_id"),
                name="uniq_open_role_assignment",
                nulls_distinct=False,
            ),
        ),
    ]
