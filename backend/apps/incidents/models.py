import datetime

from django.db import models
from django.utils import timezone

from core.models import BaseModel

ENISA_INCIDENT_CATEGORIES = [
    ("malicious_code", "Malicious Code", "Ransomware, virus, trojan, worm, spyware, cryptominer"),
    ("availability_attack", "Availability Attack", "DDoS, sabotaggio fisico, interruzione alimentazione"),
    ("information_gathering", "Information Gathering", "Scanning, sniffing, phishing, social engineering"),
    ("intrusion_attempt", "Intrusion Attempt", "Exploit di vulnerabilita, brute force, credential stuffing"),
    ("intrusion", "Intrusion", "Compromissione account, sistema o applicazione"),
    ("data_breach", "Information Security Breach", "Violazione dati personali, accesso non autorizzato a dati"),
    ("fraud", "Fraud", "Frode, impersonificazione, uso non autorizzato risorse"),
    ("supply_chain", "Supply Chain Attack", "Attacco tramite fornitore o software di terze parti"),
    ("insider_threat", "Insider Threat", "Azione dolosa o negligente da personale interno"),
    ("physical", "Physical Attack", "Danno fisico a infrastrutture, furto hardware"),
    ("other", "Other", "Incidente non classificabile nelle categorie precedenti"),
]

ENISA_SUBCATEGORIES = {
    "malicious_code": [
        ("ransomware", "Ransomware"),
        ("virus", "Virus/Worm"),
        ("trojan", "Trojan/Backdoor"),
        ("spyware", "Spyware/Stalkerware"),
        ("cryptominer", "Cryptominer"),
        ("other_malware", "Altro malware"),
    ],
    "availability_attack": [
        ("ddos", "DDoS"),
        ("dos", "DoS"),
        ("physical_damage", "Danno fisico"),
        ("power_outage", "Interruzione alimentazione"),
        ("other_avail", "Altra interruzione"),
    ],
    "intrusion": [
        ("account_compromise", "Compromissione account"),
        ("system_compromise", "Compromissione sistema"),
        ("app_compromise", "Compromissione applicazione"),
        ("ot_compromise", "Compromissione sistema OT/ICS"),
    ],
    "data_breach": [
        ("personal_data", "Dati personali (GDPR)"),
        ("confidential", "Dati riservati aziendali"),
        ("credentials", "Credenziali di accesso"),
        ("ip", "Proprieta intellettuale"),
    ],
}


class Incident(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    detected_at = models.DateTimeField()
    severity = models.CharField(
        max_length=10,
        choices=[("bassa", "bassa"), ("media", "media"), ("alta", "alta"), ("critica", "critica")],
        db_index=True,
    )
    nis2_notifiable = models.CharField(
        max_length=20,
        choices=[("si", "si"), ("no", "no"), ("da_valutare", "da_valutare")],
        default="da_valutare",
        db_index=True,
    )
    assets = models.ManyToManyField("assets.Asset", blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("aperto", "aperto"), ("in_analisi", "in_analisi"), ("chiuso", "chiuso")],
        default="aperto",
        db_index=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_incidents",
    )
    incident_category = models.CharField(
        max_length=50,
        choices=[(c[0], c[1]) for c in ENISA_INCIDENT_CATEGORIES],
        blank=True,
        help_text="Categoria ENISA — obbligatoria per notifica NIS2",
    )
    incident_subcategory = models.CharField(max_length=50, blank=True, help_text="Sottocategoria ENISA")
    affected_users_count = models.IntegerField(null=True, blank=True, help_text="Numero utenti/sistemi colpiti")
    financial_impact_eur = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="Impatto finanziario stimato in EUR"
    )
    service_disruption_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Durata interruzione servizio in ore"
    )
    personal_data_involved = models.BooleanField(default=False, help_text="Coinvolge dati personali (overlap GDPR)")
    cross_border_impact = models.BooleanField(default=False, help_text="Impatto su piu stati membri UE")
    critical_infrastructure_impact = models.BooleanField(
        default=False, help_text="Impatto su infrastrutture critiche"
    )
    is_significant = models.BooleanField(
        null=True,
        help_text="True=significativo (obbligo notifica), False=non significativo, None=da valutare",
    )
    significance_override = models.BooleanField(null=True, help_text="Override manuale della classificazione automatica")
    significance_override_reason = models.TextField(blank=True, help_text="Motivazione override obbligatoria")
    early_warning_deadline = models.DateTimeField(
        null=True, blank=True, help_text="Scadenza Early Warning T+24h (solo Essenziale)"
    )
    formal_notification_deadline = models.DateTimeField(
        null=True, blank=True, help_text="Scadenza Notifica Formale T+72h"
    )
    final_report_deadline = models.DateField(null=True, blank=True, help_text="Scadenza Report Finale T+1 mese")
    nis2_incident_ref = models.CharField(max_length=100, blank=True, help_text="Riferimento univoco assegnato dal CSIRT")

    @property
    def nis2_timeline_status(self) -> dict:
        now = timezone.now()

        def _step_status(deadline, completed: bool) -> str:
            if completed:
                return "completed"
            if not deadline:
                return "not_applicable"
            if isinstance(deadline, datetime.date) and not isinstance(deadline, datetime.datetime):
                dl = timezone.make_aware(datetime.datetime.combine(deadline, datetime.time.min))
            else:
                dl = deadline
            delta = (dl - now).total_seconds() / 3600
            if delta < 0:
                return "overdue"
            if delta < 6:
                return "due_soon"
            return "pending"

        notifications = {n.notification_type: n for n in self.nis2_notifications.all()}
        steps = []
        entity_type = self.plant.nis2_scope if self.plant else "importante"

        if entity_type == "essenziale":
            steps.append(
                {
                    "step": "early_warning",
                    "label": "Early Warning (T+24h)",
                    "deadline": self.early_warning_deadline,
                    "status": _step_status(self.early_warning_deadline, "early_warning" in notifications),
                    "completed": "early_warning" in notifications,
                }
            )

        steps.append(
            {
                "step": "formal_notification",
                "label": "Notifica Formale (T+72h)",
                "deadline": self.formal_notification_deadline,
                "status": _step_status(self.formal_notification_deadline, "formal_notification" in notifications),
                "completed": "formal_notification" in notifications,
            }
        )
        steps.append(
            {
                "step": "final_report",
                "label": "Report Finale (T+1 mese)",
                "deadline": self.final_report_deadline,
                "status": _step_status(self.final_report_deadline, "final_report" in notifications),
                "completed": "final_report" in notifications,
            }
        )
        return {
            "entity_type": entity_type,
            "steps": steps,
            "all_done": all(s["completed"] for s in steps),
        }


class IncidentNotification(BaseModel):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(max_length=50)
    sent_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)


class RCA(BaseModel):
    incident = models.OneToOneField(
        Incident,
        on_delete=models.CASCADE,
        related_name="rca",
    )
    summary = models.TextField()
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_rca",
    )


class NIS2Notification(BaseModel):
    NOTIFICATION_TYPES = [
        ("early_warning", "Early Warning (T+24h)"),
        ("formal_notification", "Notifica Formale (T+72h)"),
        ("final_report", "Report Finale (T+1 mese)"),
        ("update", "Aggiornamento intermedio"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="nis2_notifications")
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    csirt_name = models.CharField(max_length=200)
    csirt_portal = models.URLField(blank=True)
    csirt_country = models.CharField(max_length=10)
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_nis2_notifications"
    )
    protocol_ref = models.CharField(max_length=200, blank=True, help_text="Numero di protocollo ricevuto dal CSIRT")
    authority_response = models.TextField(blank=True, help_text="Note sulla risposta dell'autorita")
    document_content = models.TextField(
        blank=True, help_text="HTML del documento generato al momento dell'invio"
    )

    class Meta:
        ordering = ["generated_at"]
        unique_together = ["incident", "notification_type"]

    def __str__(self):
        return f"{self.get_notification_type_display()} — Incidente {self.incident_id}"


class NIS2Configuration(BaseModel):
    plant = models.OneToOneField("plants.Plant", on_delete=models.CASCADE, related_name="nis2_config")
    threshold_users = models.IntegerField(
        default=100, help_text="Soglia utenti colpiti per classificare significativo"
    )
    threshold_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=4.0, help_text="Soglia ore interruzione per classificare significativo"
    )
    threshold_financial = models.DecimalField(
        max_digits=12, decimal_places=2, default=100000, help_text="Soglia impatto finanziario EUR per classificare significativo"
    )
    nis2_sector = models.CharField(max_length=100, blank=True, help_text="Settore NIS2 es. 'Manifattura - Automotive'")
    nis2_subsector = models.CharField(max_length=100, blank=True, help_text="Sottosettore es. 'Produzione veicoli a motore'")
    internal_contact_name = models.CharField(max_length=200, blank=True)
    internal_contact_email = models.CharField(max_length=200, blank=True)
    internal_contact_phone = models.CharField(max_length=50, blank=True)
    legal_entity_name = models.CharField(
        max_length=300, blank=True, help_text="Ragione sociale completa per le notifiche formali"
    )
    legal_entity_vat = models.CharField(max_length=50, blank=True, help_text="Partita IVA / VAT number")

    class Meta:
        verbose_name = "NIS2 Configuration"

