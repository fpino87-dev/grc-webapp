import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0003_supplier_email_evaluation_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionnaireTemplate",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("subject", models.CharField(max_length=300)),
                ("body", models.TextField()),
                ("form_url", models.URLField(max_length=500)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SupplierQuestionnaire",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questionnaires",
                        to="suppliers.supplier",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_questionnaires",
                        to="suppliers.questionnairetemplate",
                    ),
                ),
                ("subject_snapshot", models.CharField(blank=True, max_length=300)),
                ("body_snapshot", models.TextField(blank=True)),
                ("form_url_snapshot", models.URLField(blank=True, max_length=500)),
                ("sent_at", models.DateTimeField()),
                ("last_sent_at", models.DateTimeField()),
                ("sent_to", models.EmailField()),
                (
                    "sent_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_questionnaires",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("send_count", models.PositiveSmallIntegerField(default=1)),
                ("evaluation_date", models.DateField(blank=True, null=True)),
                (
                    "risk_result",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("basso", "Basso"),
                            ("medio", "Medio"),
                            ("alto", "Alto"),
                            ("critico", "Critico"),
                        ],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("inviato", "In attesa"),
                            ("risposto", "Risposto"),
                            ("scaduto", "Scaduto"),
                        ],
                        default="inviato",
                        max_length=10,
                    ),
                ),
                ("expires_at", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={"ordering": ["-sent_at"]},
        ),
    ]
