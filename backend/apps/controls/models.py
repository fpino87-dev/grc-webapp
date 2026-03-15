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
    evidence_requirement = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Struttura: {documents:[{type,mandatory,description}], "
            "evidences:[{type,mandatory,max_age_days,description}], "
            "min_documents, min_evidences, notes}"
        ),
    )
    control_category = models.CharField(
        max_length=20,
        choices=[
            ("tecnico",       "Tecnico"),
            ("procedurale",   "Procedurale"),
            ("organizzativo", "Organizzativo"),
            ("composito",     "Composito"),
        ],
        default="procedurale",
        blank=True,
    )

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

    needs_revaluation = models.BooleanField(
        default=False,
        help_text="True se un change recente richiede rivalutazione",
    )
    needs_revaluation_since = models.DateField(null=True, blank=True)

    # Applicabilità per SOA ISO 27001
    applicability = models.CharField(
        max_length=20,
        choices=[
            ("applicabile",    "Applicabile"),
            ("escluso",        "Escluso"),
            ("non_pertinente", "Non pertinente"),
        ],
        default="applicabile",
    )
    exclusion_justification = models.TextField(
        blank=True,
        help_text="Obbligatorio se applicability=escluso. Motivazione formale per SOA ISO 27001.",
    )

    # Maturity level per VDA ISA TISAX (0-5)
    maturity_level = models.IntegerField(
        null=True, blank=True,
        help_text="0=non implementato, 1=ad-hoc, 2=pianificato, 3=definito, 4=gestito, 5=ottimizzato",
    )
    maturity_level_override = models.BooleanField(
        default=False,
        help_text="Se True il maturity_level è stato inserito manualmente e non viene ricalcolato automaticamente",
    )

    # Approvazione SOA
    approved_in_soa = models.BooleanField(default=False)
    soa_approved_at = models.DateTimeField(null=True, blank=True)
    soa_approved_by = models.ForeignKey(
        "auth.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="soa_approved_instances",
    )

    evidences = models.ManyToManyField(
        "documents.Evidence",
        blank=True,
        related_name="control_instances",
    )

    class Meta:
        unique_together = ["plant", "control"]

    @property
    def calc_maturity_level(self) -> int:
        """Calcola maturity level 0-5 da status + evidenze per VDA ISA TISAX."""
        if self.maturity_level_override and self.maturity_level is not None:
            return self.maturity_level
        from django.utils import timezone
        today = timezone.now().date()
        status_map = {"non_valutato": 0, "gap": 1, "na": 2}
        if self.status in status_map:
            return status_map[self.status]
        if self.status == "parziale":
            has_ev = self.evidences.filter(valid_until__gte=today, deleted_at__isnull=True).exists()
            return 3 if has_ev else 2
        if self.status == "compliant":
            ev_count = self.evidences.filter(valid_until__gte=today, deleted_at__isnull=True).count()
            return 5 if ev_count >= 2 else 4
        return 0

