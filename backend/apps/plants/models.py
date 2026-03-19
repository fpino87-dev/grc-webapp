from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class BusinessUnit(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    manager = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


class Plant(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=2)
    bu = models.ForeignKey(
        BusinessUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plants",
    )
    parent_plant = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_plants",
    )
    has_ot = models.BooleanField(default=False)
    purdue_level_max = models.IntegerField(null=True, blank=True)
    nis2_scope = models.CharField(
        max_length=20,
        choices=[
            ("essenziale", "Essenziale"),
            ("importante", "Importante"),
            ("non_soggetto", "Non soggetto"),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("attivo", "Attivo"),
            ("in_dismissione", "In dismissione"),
            ("chiuso", "Chiuso"),
        ],
        default="attivo",
    )
    address = models.TextField(blank=True)
    timezone = models.CharField(max_length=50, default="Europe/Rome")
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL del logo per questo sito (usato in report/export). Può essere assoluto o relativo (es. /media/...).",
    )

    class Meta:
        ordering = ["code"]

    def clean(self):
        if self.parent_plant and self.parent_plant.parent_plant:
            raise ValidationError(_("Max 1 livello di nesting per i sub-plant."))

    @property
    def is_nis2_subject(self):
        return self.nis2_scope in ("essenziale", "importante")


class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="frameworks")
    framework = models.ForeignKey("controls.Framework", on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["plant", "framework"]

