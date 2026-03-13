from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField

from core.models import BaseModel


class NormativeRole(models.TextChoices):
    CISO = "ciso", _("CISO")
    PLANT_SECURITY_OFFICER = "plant_security_officer", _("Plant Security Officer")
    NIS2_CONTACT = "nis2_contact", _("Contatto NIS2")
    DPO = "dpo", _("DPO")
    ISMS_MANAGER = "isms_manager", _("ISMS Manager")
    INTERNAL_AUDITOR = "internal_auditor", _("Auditor Interno")
    COMITATO_MEMBRO = "comitato_membro", _("Membro Comitato")
    BU_REFERENTE = "bu_referente", _("Referente BU")
    RACI_RESPONSIBLE = "raci_responsible", _("RACI Responsible")
    RACI_ACCOUNTABLE = "raci_accountable", _("RACI Accountable")


class RoleAssignment(BaseModel):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=50, choices=NormativeRole.choices)
    scope_type = models.CharField(
        max_length=20,
        choices=[("org", "Org"), ("bu", "BU"), ("plant", "Plant")],
    )
    scope_id = models.UUIDField(null=True, blank=True)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    signed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signed_assignments",
    )
    document_id = models.UUIDField(null=True, blank=True)
    framework_refs = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    notes = models.TextField(blank=True)

    @property
    def is_active(self):
        from django.utils import timezone

        today = timezone.now().date()
        return self.valid_from <= today and (
            self.valid_until is None or self.valid_until >= today
        )


class SecurityCommittee(BaseModel):
    plant = models.ForeignKey(
        "plants.Plant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=200)
    committee_type = models.CharField(
        max_length=20,
        choices=[("centrale", "Centrale"), ("bu", "BU")],
    )
    frequency = models.CharField(
        max_length=20,
        choices=[
            ("mensile", "Mensile"),
            ("trimestrale", "Trimestrale"),
            ("semestrale", "Semestrale"),
        ],
    )
    next_meeting_at = models.DateTimeField(null=True, blank=True)


class CommitteeMeeting(BaseModel):
    committee = models.ForeignKey(
        SecurityCommittee,
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    held_at = models.DateTimeField()
    verbale_doc_id = models.UUIDField(null=True, blank=True)
    delibere = models.JSONField(default=list)
    attendees = models.ManyToManyField("auth.User", blank=True)

    class Meta:
        ordering = ["-held_at"]

