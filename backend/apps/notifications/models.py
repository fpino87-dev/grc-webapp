from django.db import models

from core.models import BaseModel


NON_DISATTIVABILI = {"nis2_timer_alert", "risk_red_threshold", "delegation_expiring"}


class NotificationSubscription(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="notification_subscriptions")
    event_type = models.CharField(max_length=100)
    channel = models.CharField(max_length=50, default="email")
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "event_type", "channel")

    def save(self, *args, **kwargs):
        if self.event_type in NON_DISATTIVABILI:
            self.enabled = True  # non può essere disabilitato
        super().save(*args, **kwargs)

