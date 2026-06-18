from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Task(BaseModel):
    PRIORITY_CHOICES = [
        ("bassa", "Bassa"),
        ("media", "Media"),
        ("alta", "Alta"),
        ("critica", "Critica"),
    ]
    STATUS_CHOICES = [
        ("aperto", "Aperto"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("annullato", "Annullato"),
        ("scaduto", "Scaduto"),
    ]
    SOURCE_CHOICES = [
        ("manuale", "Manuale"),
        ("controllo", "Controllo"),
        ("rischio", "Rischio"),
        ("incidente", "Incidente"),
        ("pdca", "PDCA"),
        ("audit", "Audit"),
    ]
    RECURRENCE_CHOICES = [
        ("none", "Nessuna"),
        ("daily", "Giornaliera"),
        ("weekly", "Settimanale"),
        ("monthly", "Mensile"),
        ("quarterly", "Trimestrale"),
        ("yearly", "Annuale"),
    ]

    source_module = models.CharField(max_length=10, blank=True, default="")
    source_id     = models.UUIDField(null=True, blank=True)

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tasks",
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="media",
        db_index=True,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="aperto",
        db_index=True,
    )
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default="manuale")

    assigned_role = models.CharField(max_length=50, blank=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_tasks",
    )

    # Relations to source objects
    control_instance = models.ForeignKey(
        "controls.ControlInstance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    risk_assessment = models.ForeignKey(
        "risk.RiskAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    # Recurrence
    recurrence = models.CharField(
        max_length=15, choices=RECURRENCE_CHOICES, default="none"
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurrence_children",
    )

    # Escalation
    escalation_level = models.PositiveSmallIntegerField(default=0)
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalated_tasks",
    )
    escalated_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date", "-priority"]


class TaskComment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField()

    class Meta:
        ordering = ["task_id", "created_at"]


# ── Quick Checklist (M08) ────────────────────────────────────────────────────
# Checklist operative ricorrenti: template riutilizzabili + run giornalieri
# generati automaticamente via Celery. Pensate per essere completate in 30s,
# senza workflow di approvazione.


class ChecklistTemplate(BaseModel):
    FREQUENCY_CHOICES = [
        ("daily", "Giornaliera"),
        ("weekly", "Settimanale"),
        ("monthly", "Mensile"),
        ("ad_hoc", "Ad hoc"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default="daily", db_index=True
    )
    # Giorni della settimana (0=lunedì … 6=domenica, come date.weekday()) in cui
    # generare il run. Si applica SOLO a frequency="daily": lista vuota = tutti i
    # 7 giorni (comportamento storico). Permette es. [0,1,2,3,4] per attività
    # solo feriali, evitando run di sabato/domenica che resterebbero "overdue" e
    # falserebbero i KPI basati su checklist.
    days_of_week = models.JSONField(
        default=list,
        blank=True,
        help_text="Solo per frequenza giornaliera: giorni 0-6 (lun-dom). Vuoto=tutti.",
    )
    # plant null = template valido per tutti i plant
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checklist_templates",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]


class ChecklistTemplateItem(BaseModel):
    ITEM_TYPE_CHOICES = [
        ("checkbox", "Checkbox"),
        ("numeric", "Numerico"),
        ("text", "Testo libero"),
    ]

    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.CASCADE, related_name="items"
    )
    order = models.IntegerField(default=0)
    text = models.CharField(max_length=500)
    is_mandatory = models.BooleanField(default=True)
    # Tipologia di rilevazione: checkbox (default, retrocompatibile), valore
    # numerico (per KPI) o testo libero.
    item_type = models.CharField(
        max_length=10, choices=ITEM_TYPE_CHOICES, default="checkbox"
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Es: %, ore, GB, n° — solo per item_type=numeric",
    )
    numeric_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valore minimo accettabile per item numeric",
    )
    numeric_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["order", "created_at"]


class ChecklistRun(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Da iniziare"),
        ("in_progress", "In corso"),
        ("completed", "Completata"),
        ("overdue", "Scaduta"),
    ]

    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.PROTECT, related_name="runs"
    )
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        related_name="checklist_runs",
        db_index=True,
    )
    # assegnazione diretta opzionale: i run auto-generati nascono senza assegnatario
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_checklist_runs",
    )
    due_date = models.DateField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_checklist_runs",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    class Meta:
        ordering = ["-due_date", "template__name"]


class ChecklistRunItem(BaseModel):
    run = models.ForeignKey(
        ChecklistRun, on_delete=models.CASCADE, related_name="items"
    )
    template_item = models.ForeignKey(
        ChecklistTemplateItem, on_delete=models.PROTECT, related_name="run_items"
    )
    checked = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checked_checklist_items",
    )
    # Valorizzati in base a template_item.item_type (numeric / text).
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valorizzato solo se template_item.item_type=numeric",
    )
    text_value = models.TextField(
        blank=True,
        help_text="Valorizzato solo se template_item.item_type=text",
    )

    class Meta:
        ordering = ["template_item__order", "created_at"]


# ── KPI Engine operativo (M08 ↔ M18) ─────────────────────────────────────────
# Motore KPI con soglie e alerting. Le definizioni descrivono COSA misurare e
# COME aggregare; gli snapshot sono i valori settimanali calcolati. Sorgenti:
# checklist (aggregazione run), API esterna (ingest), inserimento manuale.


class KPIDefinition(BaseModel):
    AGGREGATION_CHOICES = [
        ("success_rate", "Tasso di successo (% run completati)"),
        ("avg_value", "Media valori numerici"),
        ("last_value", "Ultimo valore registrato"),
        ("count_ok", "Conteggio item OK"),
        ("count_fail", "Conteggio item KO"),
    ]
    SOURCE_CHOICES = [
        ("checklist", "Checklist"),
        ("internal", "Modulo interno (auto-calcolo)"),
        ("api", "API esterna"),
        ("manual", "Inserimento manuale"),
    ]
    DIRECTION_CHOICES = [
        ("above", "Sopra soglia=ok"),
        ("below", "Sotto soglia=ok"),
    ]

    kpi_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Es: backup_success_rate, vuln_critical_open",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, blank=True, help_text="%, ore, n°")
    source = models.CharField(
        max_length=15, choices=SOURCE_CHOICES, default="checklist", db_index=True
    )
    checklist_template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kpi_definitions",
        help_text="Template sorgente se source=checklist",
    )
    checklist_item_filter = models.CharField(
        max_length=500,
        blank=True,
        help_text="Testo parziale item da aggregare, blank=tutti",
    )
    aggregation = models.CharField(
        max_length=20, choices=AGGREGATION_CHOICES, default="success_rate"
    )
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="kpi_definitions",
        help_text="null=KPI globale multi-plant",
        db_index=True,
    )
    threshold_warning = models.FloatField(null=True, blank=True)
    threshold_critical = models.FloatField(null=True, blank=True)
    threshold_direction = models.CharField(
        max_length=5,
        choices=DIRECTION_CHOICES,
        default="above",
        help_text=(
            "above: valore alto è buono (es success_rate). "
            "below: valore basso è buono (es vuln aperte)"
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notify_on_warning = models.BooleanField(default=True)
    notify_on_critical = models.BooleanField(default=True)

    class Meta:
        ordering = ["kpi_code"]


class OperationalKpiSnapshot(BaseModel):
    STATUS_CHOICES = [
        ("ok", "OK"),
        ("warning", "Warning"),
        ("critical", "Critico"),
        ("no_data", "Nessun dato"),
    ]

    kpi_definition = models.ForeignKey(
        KPIDefinition, on_delete=models.PROTECT, related_name="snapshots"
    )
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="operational_kpi_snapshots",
    )
    week_start = models.DateField(help_text="Lunedì della settimana", db_index=True)
    value = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="no_data", db_index=True
    )
    source = models.CharField(
        max_length=15, choices=KPIDefinition.SOURCE_CHOICES, default="checklist"
    )
    measured_at = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(
        default=0, help_text="N run analizzati per questo snapshot"
    )
    note = models.TextField(blank=True)

    class Meta:
        unique_together = [("kpi_definition", "plant", "week_start")]
        ordering = ["-week_start"]
