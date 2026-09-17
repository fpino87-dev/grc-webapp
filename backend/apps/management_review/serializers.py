from rest_framework import serializers

from apps.auth_grc.models import GrcRole

from .models import ManagementReview, ReviewAction, ReviewAgendaItem


def _user_label(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.email


class ReviewActionSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    objective_code = serializers.CharField(source="security_objective.code", read_only=True, allow_null=True)
    objective_status = serializers.CharField(source="security_objective.status", read_only=True, allow_null=True)
    task_status = serializers.CharField(source="task.status", read_only=True, allow_null=True)
    task_title = serializers.CharField(source="task.title", read_only=True, allow_null=True)
    pdca_phase = serializers.CharField(source="pdca_cycle.fase_corrente", read_only=True, allow_null=True)
    pdca_title = serializers.CharField(source="pdca_cycle.title", read_only=True, allow_null=True)

    # Solo in creazione: apertura di task (M08) e/o ciclo PDCA (M11) collegati.
    create_task = serializers.BooleanField(write_only=True, required=False, default=False)
    task_role = serializers.ChoiceField(
        choices=[c for c in GrcRole.choices if c[0] != GrcRole.SUPER_ADMIN],
        write_only=True, required=False, allow_blank=True,
    )
    create_pdca = serializers.BooleanField(write_only=True, required=False, default=False)
    pdca_plant = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    # Obiettivo di sicurezza deliberato dal riesame (§6.2): i campi del piano
    # arrivano come oggetto unico, validato dai servizi di governance.
    objective = serializers.JSONField(write_only=True, required=False, allow_null=True)

    def get_owner_name(self, obj):
        return _user_label(obj.owner) if obj.owner else None

    class Meta:
        model = ReviewAction
        fields = "__all__"
        read_only_fields = [
            "id", "task", "pdca_cycle", "security_objective", "closed_at",
            "created_by", "created_at", "updated_at", "deleted_at",
        ]

    def validate(self, attrs):
        if self.instance is not None:
            # review e punto non si spostano dopo la creazione
            attrs.pop("review", None)
            for key in ("create_task", "task_role", "create_pdca", "pdca_plant", "objective"):
                attrs.pop(key, None)
        return attrs


class ReviewAgendaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewAgendaItem
        fields = ["id", "review", "code", "title", "order", "mandatory", "discussion", "updated_at"]
        read_only_fields = ["id", "code", "order", "mandatory", "updated_at"]

    def validate(self, attrs):
        if self.instance is not None:
            attrs.pop("review", None)
        return attrs


class ManagementReviewSerializer(serializers.ModelSerializer):
    actions = ReviewActionSerializer(many=True, read_only=True)
    agenda_items = ReviewAgendaItemSerializer(many=True, read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)
    chair_name = serializers.SerializerMethodField()
    attendees_detail = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    def get_chair_name(self, obj):
        return _user_label(obj.chair) if obj.chair else None

    def get_attendees_detail(self, obj):
        return [{"id": u.pk, "name": _user_label(u)} for u in obj.attendees.all()]

    def get_approved_by_name(self, obj):
        return _user_label(obj.approved_by) if obj.approved_by else None

    class Meta:
        model = ManagementReview
        exclude = ["agenda", "delibere"]
        # L'approvazione formale (ISO 27001 §9.3) e lo snapshot dei dati sono
        # governati dalle azioni `approve` / `generate-snapshot` / `complete`
        # (con prerequisiti e audit). Senza questo lock una PATCH potrebbe
        # impostare uno `snapshot_generated_at` fittizio e poi marcare il
        # riesame `approvato` falsificando approvatore e data, scavalcando lo
        # snapshot reale e l'audit. Anche lo stato della riunione passa dalle
        # azioni `start` / `complete` (la chiusura verifica l'ordine del giorno)
        # e la sintesi dagli endpoint dedicati (bozza IA → accettazione umana).
        read_only_fields = [
            "id",
            "status",
            "approval_status",
            "approved_by",
            "approved_at",
            "approval_note",
            "snapshot_generated_at",
            "snapshot_data",
            "kpi_snapshot",
            "executive_summary",
            "executive_summary_meta",
            "executive_summary_draft",
            "executive_summary_draft_meta",
            "document_id",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
