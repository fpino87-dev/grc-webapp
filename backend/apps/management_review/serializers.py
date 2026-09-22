from rest_framework import serializers

from apps.auth_grc.models import GrcRole

from .models import ManagementReview, ReviewAction, ReviewAgendaItem, ReviewParticipant


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
        fields = [
            "id", "review", "code", "title", "order", "mandatory", "discussion",
            "discussion_meta", "discussion_draft", "discussion_draft_meta", "updated_at",
        ]
        # La bozza IA e la sua provenienza non si scrivono via PATCH: passano
        # dalle azioni discussion-draft / discussion, che registrano chi ha
        # validato il testo (CLAUDE.md #9).
        read_only_fields = [
            "id", "code", "order", "mandatory", "updated_at",
            "discussion_meta", "discussion_draft", "discussion_draft_meta",
        ]

    def validate(self, attrs):
        if self.instance is not None:
            attrs.pop("review", None)
        return attrs


class ReviewParticipantSerializer(serializers.ModelSerializer):
    has_account = serializers.SerializerMethodField()

    class Meta:
        model = ReviewParticipant
        fields = [
            "id", "member", "user", "full_name", "position", "body_role", "is_chair",
            "attendance", "delegate_name", "order", "has_account",
        ]
        read_only_fields = fields

    def get_has_account(self, obj):
        return obj.user_id is not None


class ManagementReviewSerializer(serializers.ModelSerializer):
    actions = ReviewActionSerializer(many=True, read_only=True)
    agenda_items = ReviewAgendaItemSerializer(many=True, read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)
    participants = ReviewParticipantSerializer(many=True, read_only=True)
    chair_name = serializers.SerializerMethodField()
    governing_body_name = serializers.CharField(source="governing_body.name", read_only=True, allow_null=True)
    report_logo_plant_code = serializers.CharField(source="report_logo_plant.code", read_only=True, allow_null=True)
    approved_by_name = serializers.SerializerMethodField()
    approved_member_name = serializers.SerializerMethodField()
    viewer_can_approve = serializers.SerializerMethodField()
    approved_documents = serializers.SerializerMethodField()

    def get_approved_documents(self, obj):
        """Documenti mandati in vigore con l'approvazione di questo riesame.

        Solo nel dettaglio: in elenco sarebbe una query per riga (regola #6),
        e la lista dei riesami non ne ha bisogno.
        """
        if self.parent is not None:
            return []
        from apps.documents.models import DocumentApproval

        return [
            {"id": str(a.document_id), "title": a.document.title,
             "document_code": a.document.document_code}
            for a in DocumentApproval.objects.filter(
                review_id=obj.pk, action="approve", deleted_at__isnull=True,
            ).select_related("document").order_by("created_at")
        ]

    def get_chair_name(self, obj):
        chair = next((p for p in obj.participants.all() if p.is_chair), None)
        return chair.full_name if chair else None

    def get_approved_by_name(self, obj):
        return _user_label(obj.approved_by) if obj.approved_by else None

    def get_approved_member_name(self, obj):
        m = obj.approved_member
        if m is None:
            return None
        return f"{m.full_name} ({m.position})" if m.position else m.full_name

    def get_viewer_can_approve(self, obj):
        # `approval_scope` = (è governance, organi in cui siede) calcolato una
        # volta per richiesta dalla view: niente query per riga (regola #6).
        scope = self.context.get("approval_scope")
        if scope is None or obj.approval_status == "approvato":
            return False
        is_governance, body_ids = scope
        return is_governance or obj.governing_body_id in body_ids

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
            "approval_mode",
            "approved_member",
            "report_logo_plant",
            "approval_resolution_ref",
            "approval_resolution_date",
            "approval_document_id",
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
