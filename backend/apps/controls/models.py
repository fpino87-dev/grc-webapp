from django.db import models

from core.models import BaseModel


class Framework(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    published_at = models.DateField()
    archived_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["code"]


class ControlDomain(BaseModel):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="domains")
    code = models.CharField(max_length=50)
    translations = models.JSONField()
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ["framework", "code"]
        ordering = ["order"]

    def get_name(self, lang: str = "it") -> str:
        return self.translations.get(lang, self.translations.get("en", {})).get("name", self.code)


class Control(BaseModel):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="controls")
    domain = models.ForeignKey(
        ControlDomain,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    external_id = models.CharField(max_length=50)
    translations = models.JSONField()
    level = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ["framework", "external_id"]

    def get_title(self, lang: str = "it") -> str:
        t = self.translations.get(lang) or self.translations.get("en", {})
        return t.get("title", self.external_id)


class ControlMapping(BaseModel):
    source_control = models.ForeignKey(
        Control,
        on_delete=models.CASCADE,
        related_name="mappings_from",
    )
    target_control = models.ForeignKey(
        Control,
        on_delete=models.CASCADE,
        related_name="mappings_to",
    )
    relationship = models.CharField(
        max_length=20,
        choices=[
            ("equivalente", "Equivalente"),
            ("parziale", "Parziale"),
            ("correlato", "Correlato"),
            ("covers", "Copre"),
            ("extends", "Estende"),
        ],
    )


class ControlInstance(BaseModel):
    plant = models.ForeignKey("plants.Plant", on_delete=models.CASCADE)
    control = models.ForeignKey(Control, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[
            ("compliant", "Compliant"),
            ("parziale", "Parziale"),
            ("gap", "Gap"),
            ("na", "N/A"),
            ("non_valutato", "Non valutato"),
        ],
        default="non_valutato",
    )
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    notes = models.TextField(blank=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    na_approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_na_instances",
    )
    na_second_approver = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="second_approved_na_instances",
    )
    na_approved_at = models.DateTimeField(null=True, blank=True)
    na_review_by = models.DateField(null=True, blank=True)
    na_justification = models.TextField(blank=True)
    last_evaluated_note = models.TextField(blank=True)
    evidences = models.ManyToManyField(
        "documents.Evidence",
        blank=True,
        related_name="control_instances",
    )

    class Meta:
        unique_together = ["plant", "control"]

