from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, editable=False, serialize=False)),
                ("timestamp_utc", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user_id", models.UUIDField()),
                ("user_email_at_time", models.CharField(max_length=255)),
                ("user_role_at_time", models.CharField(blank=True, max_length=50)),
                ("action_code", models.CharField(db_index=True, max_length=100)),
                ("level", models.CharField(choices=[("L1", "L1"), ("L2", "L2"), ("L3", "L3")], max_length=2)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.UUIDField(db_index=True)),
                ("payload", models.JSONField()),
                ("prev_hash", models.CharField(max_length=64)),
                ("record_hash", models.CharField(max_length=64)),
            ],
            options={
                "db_table": "audit_log",
                "ordering": ["-timestamp_utc"],
            },
        ),
    ]

