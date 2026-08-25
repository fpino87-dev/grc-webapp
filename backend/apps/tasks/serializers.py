from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from . import services
from .models import (
    ChecklistRun,
    ChecklistRunItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    Task,
    TaskComment,
)


class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = "__all__"


class TaskSerializer(serializers.ModelSerializer):
    comments_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = "__all__"

    def get_comments_count(self, obj):
        return obj.comments.count()


# ── Quick Checklist (M08) ────────────────────────────────────────────────────


class ChecklistTemplateItemSerializer(serializers.ModelSerializer):
    # `id` scrivibile: identifica l'item esistente da aggiornare in place
    # invece di ricrearlo (vedi services.sync_template_items).
    id = serializers.UUIDField(required=False)

    class Meta:
        model = ChecklistTemplateItem
        fields = [
            "id", "order", "text", "is_mandatory",
            "item_type", "unit", "numeric_min", "numeric_max",
        ]


class ChecklistTemplateSerializer(serializers.ModelSerializer):
    # Gestione inline degli item: il client invia l'intera lista, qui la
    # sincronizziamo (create/update/delete) in modo transazionale.
    items = ChecklistTemplateItemSerializer(many=True, required=False)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    runs_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "description", "frequency", "days_of_week",
            "day_of_month", "start_month", "plant", "plant_name",
            "facility_category", "records_maintenance",
            "is_active", "items", "runs_count", "created_at", "updated_at",
        ]

    def get_runs_count(self, obj):
        return obj.runs.count()

    def validate_days_of_week(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Deve essere una lista di giorni."))
        cleaned = []
        for day in value:
            if not isinstance(day, int) or isinstance(day, bool) or not 0 <= day <= 6:
                raise serializers.ValidationError(
                    _("I giorni devono essere interi da 0 (lun) a 6 (dom).")
                )
            if day not in cleaned:
                cleaned.append(day)
        return sorted(cleaned)

    def validate_day_of_month(self, value):
        # 0 = ultimo giorno del mese. Il massimo è 28 e non 31: un giorno più
        # avanti non esiste in ogni mese e chi vuole "fine mese" ha l'opzione
        # dedicata, che è sempre l'ultimo giorno reale.
        if value is None:
            return 1
        if not 0 <= value <= 28:
            raise serializers.ValidationError(
                _("Indicare un giorno da 1 a 28, oppure 0 per l'ultimo giorno del mese.")
            )
        return value

    def validate_start_month(self, value):
        if value is None:
            return 1
        if not 1 <= value <= 12:
            raise serializers.ValidationError(
                _("Il mese di partenza deve essere compreso fra 1 (gennaio) e 12 (dicembre).")
            )
        return value

    def validate(self, attrs):
        frequency = attrs.get("frequency") or getattr(self.instance, "frequency", "daily")
        days = attrs.get("days_of_week")
        if frequency == "weekly" and days and len(days) > 1:
            raise serializers.ValidationError({
                "days_of_week": _("Per la frequenza settimanale indicare un solo giorno.")
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        template = ChecklistTemplate.objects.create(**validated_data)
        services.sync_template_items(template, items_data)
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            services.sync_template_items(instance, items_data)
        return instance


class ChecklistRunItemSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="template_item.text", read_only=True)
    is_mandatory = serializers.BooleanField(
        source="template_item.is_mandatory", read_only=True
    )
    order = serializers.IntegerField(source="template_item.order", read_only=True)
    item_type = serializers.CharField(
        source="template_item.item_type", read_only=True
    )
    unit = serializers.CharField(source="template_item.unit", read_only=True)

    class Meta:
        model = ChecklistRunItem
        fields = [
            "id", "template_item", "text", "is_mandatory", "order",
            "item_type", "unit", "checked", "note", "value", "text_value",
            "checked_at", "checked_by",
        ]
        read_only_fields = ["checked_at", "checked_by"]


class ChecklistRunSerializer(serializers.ModelSerializer):
    items = ChecklistRunItemSerializer(many=True, read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    progress_total = serializers.SerializerMethodField(read_only=True)
    progress_done = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChecklistRun
        fields = [
            "id", "template", "template_name", "asset", "asset_name",
            "plant", "plant_name",
            "assigned_to", "due_date", "completed_at", "completed_by",
            "status", "items", "progress_total", "progress_done", "created_at",
        ]
        read_only_fields = ["completed_at", "completed_by", "created_at"]

    def get_progress_total(self, obj):
        return obj.items.count()

    def get_progress_done(self, obj):
        return obj.items.filter(checked=True).count()


# ── KPI Engine operativo (M08 ↔ M18) ─────────────────────────────────────────

import re

from .models import KPIDefinition, OperationalKpiSnapshot

_KPI_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_kpi_code(value: str) -> str:
    """kpi_code slug-like: minuscole, cifre e underscore, iniziale alfabetica."""
    if not _KPI_CODE_RE.match(value or ""):
        raise serializers.ValidationError(
            "kpi_code deve essere slug-like: solo minuscole, cifre e underscore, "
            "deve iniziare con una lettera (es: backup_success_rate)."
        )
    return value


class KPIDefinitionSerializer(serializers.ModelSerializer):
    # Dichiarato a mano per non ereditare l'UniqueValidator che DRF genera
    # dalla UniqueConstraint su kpi_code: quel validator ignora il plant e
    # bloccherebbe un sito solo perché il codice esiste altrove. L'unicità
    # corretta — per (kpi_code, plant) — è verificata in validate().
    kpi_code = serializers.CharField(max_length=50)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    checklist_template_name = serializers.CharField(
        source="checklist_template.name", read_only=True
    )
    checklist_item_text = serializers.CharField(
        source="checklist_item.text", read_only=True
    )

    class Meta:
        model = KPIDefinition
        fields = [
            "id", "kpi_code", "name", "description", "unit", "source",
            "checklist_template", "checklist_template_name",
            "checklist_item", "checklist_item_text", "checklist_item_filter",
            "aggregation",
            "plant", "plant_name",
            "threshold_warning", "threshold_critical", "threshold_direction",
            "is_active", "notify_on_warning", "notify_on_critical",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        # DRF deriva da solo dei validator di unicità dalle UniqueConstraint
        # del modello, ma il messaggio finisce in `non_field_errors` ("I campi
        # kpi_code, plant devono costituire un insieme unico") — illeggibile
        # per chi compila il form. Li disattiviamo e facciamo il controllo in
        # `validate()`, che riporta l'errore sul campo kpi_code spiegando se il
        # conflitto è sul sito o sulla definizione globale.
        validators = []

    def validate_kpi_code(self, value):
        return _validate_kpi_code(value)

    def validate(self, attrs):
        # L'unicita' di kpi_code e' per sito, non globale: due stabilimenti
        # possono tracciare lo stesso KPI con soglie proprie. Il controllo sta
        # qui e non in validate_kpi_code perche' serve anche il plant, che su
        # una PATCH parziale puo' arrivare solo dall'istanza.
        attrs = super().validate(attrs)
        code = attrs.get("kpi_code") or getattr(self.instance, "kpi_code", None)
        plant = (
            attrs["plant"] if "plant" in attrs
            else getattr(self.instance, "plant", None)
        )
        # La voce collegata deve appartenere al template del KPI: puntare alla
        # voce di un altro template darebbe un KPI che non misura mai nulla.
        item = attrs["checklist_item"] if "checklist_item" in attrs else getattr(
            self.instance, "checklist_item", None
        )
        template = (
            attrs["checklist_template"] if "checklist_template" in attrs
            else getattr(self.instance, "checklist_template", None)
        )
        if item is not None and (template is None or item.template_id != template.pk):
            raise serializers.ValidationError({"checklist_item": (
                "La voce indicata non appartiene al template selezionato."
            )})

        if code:
            qs = KPIDefinition.objects.filter(kpi_code=code, plant=plant)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"kpi_code": (
                    "Esiste già un KPI globale con questo codice."
                    if plant is None else
                    "Esiste già un KPI con questo codice per questo sito."
                )})
        return attrs


class OperationalKpiSnapshotSerializer(serializers.ModelSerializer):
    kpi_code = serializers.CharField(
        source="kpi_definition.kpi_code", read_only=True
    )
    kpi_name = serializers.CharField(source="kpi_definition.name", read_only=True)
    unit = serializers.CharField(source="kpi_definition.unit", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)

    class Meta:
        model = OperationalKpiSnapshot
        fields = [
            "id", "kpi_definition", "kpi_code", "kpi_name", "unit",
            "plant", "plant_name", "week_start", "value", "status",
            "source", "measured_at", "run_count", "note", "created_at",
        ]
        read_only_fields = fields


class KPIDefinitionListSerializer(serializers.ModelSerializer):
    """Serializer ridotto per la lista, con lo status dell'ultimo snapshot."""

    last_status = serializers.SerializerMethodField()
    last_value = serializers.SerializerMethodField()

    class Meta:
        model = KPIDefinition
        fields = [
            "id", "kpi_code", "name", "unit",
            "threshold_warning", "threshold_critical", "threshold_direction",
            "source", "is_active", "plant",
            "last_status", "last_value",
        ]

    def _last_snapshot(self, obj):
        # Sfrutta la prefetch del ViewSet se presente, altrimenti query diretta.
        snaps = getattr(obj, "_prefetched_objects_cache", {}).get("snapshots")
        if snaps is not None:
            return snaps[0] if snaps else None
        return obj.snapshots.order_by("-week_start").first()

    def get_last_status(self, obj):
        snap = self._last_snapshot(obj)
        return snap.status if snap else "no_data"

    def get_last_value(self, obj):
        snap = self._last_snapshot(obj)
        return snap.value if snap else None
