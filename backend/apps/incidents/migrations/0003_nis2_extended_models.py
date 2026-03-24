from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0002_alter_incident_nis2_notifiable_and_more"),
        ("plants", "0004_alter_plant_country"),
        ("assets", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="affected_users_count",
            field=models.IntegerField(blank=True, help_text="Numero utenti/sistemi colpiti", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="critical_infrastructure_impact",
            field=models.BooleanField(default=False, help_text="Impatto su infrastrutture critiche"),
        ),
        migrations.AddField(
            model_name="incident",
            name="cross_border_impact",
            field=models.BooleanField(default=False, help_text="Impatto su piu stati membri UE"),
        ),
        migrations.AddField(
            model_name="incident",
            name="financial_impact_eur",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Impatto finanziario stimato in EUR",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="final_report_deadline",
            field=models.DateField(blank=True, help_text="Scadenza Report Finale T+1 mese", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="formal_notification_deadline",
            field=models.DateTimeField(blank=True, help_text="Scadenza Notifica Formale T+72h", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="incident_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("malicious_code", "Malicious Code"),
                    ("availability_attack", "Availability Attack"),
                    ("information_gathering", "Information Gathering"),
                    ("intrusion_attempt", "Intrusion Attempt"),
                    ("intrusion", "Intrusion"),
                    ("data_breach", "Information Security Breach"),
                    ("fraud", "Fraud"),
                    ("supply_chain", "Supply Chain Attack"),
                    ("insider_threat", "Insider Threat"),
                    ("physical", "Physical Attack"),
                    ("other", "Other"),
                ],
                help_text="Categoria ENISA — obbligatoria per notifica NIS2",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="incident_subcategory",
            field=models.CharField(blank=True, help_text="Sottocategoria ENISA", max_length=50),
        ),
        migrations.AddField(
            model_name="incident",
            name="is_significant",
            field=models.BooleanField(
                help_text="True=significativo (obbligo notifica), False=non significativo, None=da valutare",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="nis2_incident_ref",
            field=models.CharField(
                blank=True, help_text="Riferimento univoco assegnato dal CSIRT", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="personal_data_involved",
            field=models.BooleanField(default=False, help_text="Coinvolge dati personali (overlap GDPR)"),
        ),
        migrations.AddField(
            model_name="incident",
            name="service_disruption_hours",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Durata interruzione servizio in ore", max_digits=8, null=True
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="significance_override",
            field=models.BooleanField(help_text="Override manuale della classificazione automatica", null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="significance_override_reason",
            field=models.TextField(blank=True, help_text="Motivazione override obbligatoria"),
        ),
        migrations.AddField(
            model_name="incident",
            name="early_warning_deadline",
            field=models.DateTimeField(
                blank=True, help_text="Scadenza Early Warning T+24h (solo Essenziale)", null=True
            ),
        ),
        migrations.CreateModel(
            name="NIS2Configuration",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("threshold_users", models.IntegerField(default=100, help_text="Soglia utenti colpiti per classificare significativo")),
                ("threshold_hours", models.DecimalField(decimal_places=2, default=4.0, help_text="Soglia ore interruzione per classificare significativo", max_digits=6)),
                ("threshold_financial", models.DecimalField(decimal_places=2, default=100000, help_text="Soglia impatto finanziario EUR per classificare significativo", max_digits=12)),
                ("nis2_sector", models.CharField(blank=True, help_text="Settore NIS2 es. 'Manifattura - Automotive'", max_length=100)),
                ("nis2_subsector", models.CharField(blank=True, help_text="Sottosettore es. 'Produzione veicoli a motore'", max_length=100)),
                ("internal_contact_name", models.CharField(blank=True, max_length=200)),
                ("internal_contact_email", models.CharField(blank=True, max_length=200)),
                ("internal_contact_phone", models.CharField(blank=True, max_length=50)),
                ("legal_entity_name", models.CharField(blank=True, help_text="Ragione sociale completa per le notifiche formali", max_length=300)),
                ("legal_entity_vat", models.CharField(blank=True, help_text="Partita IVA / VAT number", max_length=50)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="+", to="auth.user")),
                ("plant", models.OneToOneField(on_delete=models.CASCADE, related_name="nis2_config", to="plants.plant")),
            ],
            options={"verbose_name": "NIS2 Configuration"},
        ),
        migrations.CreateModel(
            name="NIS2Notification",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notification_type", models.CharField(choices=[("early_warning", "Early Warning (T+24h)"), ("formal_notification", "Notifica Formale (T+72h)"), ("final_report", "Report Finale (T+1 mese)"), ("update", "Aggiornamento intermedio")], max_length=30)),
                ("csirt_name", models.CharField(max_length=200)),
                ("csirt_portal", models.URLField(blank=True)),
                ("csirt_country", models.CharField(max_length=10)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("protocol_ref", models.CharField(blank=True, help_text="Numero di protocollo ricevuto dal CSIRT", max_length=200)),
                ("authority_response", models.TextField(blank=True, help_text="Note sulla risposta dell'autorita")),
                ("document_content", models.TextField(blank=True, help_text="HTML del documento generato al momento dell'invio")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="+", to="auth.user")),
                ("incident", models.ForeignKey(on_delete=models.CASCADE, related_name="nis2_notifications", to="incidents.incident")),
                ("sent_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="sent_nis2_notifications", to="auth.user")),
            ],
            options={"ordering": ["generated_at"], "unique_together": {("incident", "notification_type")}},
        ),
    ]
