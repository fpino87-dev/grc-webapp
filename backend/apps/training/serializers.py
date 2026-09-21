from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.governance.models import CommitteeMember

from .models import (
    TrainingAudience,
    TrainingCourse,
    TrainingEvidenceControl,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)


class TrainingCourseSerializer(serializers.ModelSerializer):
    # Ambito: nessun sito = corso di organizzazione.
    plant_codes = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCourse
        fields = [
            "id",
            "title",
            "source",
            "status",
            "kb4_campaign_id",
            "description",
            "duration_minutes",
            "mandatory",
            "plants",
            "plant_codes",
            "deadline",
            "kind",
            "audience_kind",
            "validity_months",
            "competency",
            "competency_level",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]

    def get_plant_codes(self, obj):
        return sorted(p.code for p in obj.plants.all())


def control_option(control, lang="it") -> dict:
    return {
        "id": str(control.pk),
        "external_id": control.external_id,
        "framework_code": control.framework.code,
        "title": control.get_title(lang),
    }


_SYSTEM = ["id", "created_at", "updated_at", "created_by"]


class TrainingEvidenceControlSerializer(serializers.ModelSerializer):
    control_detail = serializers.SerializerMethodField()

    class Meta:
        model = TrainingEvidenceControl
        fields = ["id", "audience_kind", "control", "control_detail",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM
        validators = []

    def get_control_detail(self, obj):
        lang = getattr(self.context.get("request"), "LANGUAGE_CODE", "it")
        return control_option(obj.control, lang)


class TrainingAudienceSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True)

    class Meta:
        model = TrainingAudience
        fields = ["id", "plant", "plant_code", "name", "headcount", "headcount_updated_at", "notes",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM + ["headcount_updated_at"]
        # Unicità (plant, name) garantita dal vincolo DB condizionale sul soft delete.
        validators = []


class TrainingPlanItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = TrainingPlanItem
        fields = ["id", "plan", "course", "course_title", "audiences", "due_date", "notes",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM


class TrainingPlanSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True, default=None)
    document_status = serializers.CharField(source="document.status", read_only=True, default=None)
    document_title = serializers.CharField(source="document.title", read_only=True, default=None)

    class Meta:
        model = TrainingPlan
        fields = ["id", "plant", "plant_code", "year", "document", "document_status",
                  "document_title", "notes",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM
        validators = []


class TrainingSessionSerializer(serializers.ModelSerializer):
    # Il file arriva in multipart solo alla registrazione: diventa l'evidenza.
    file = serializers.FileField(write_only=True, required=False)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_kind = serializers.CharField(source="course.kind", read_only=True)
    plant_code = serializers.CharField(source="plant.code", read_only=True, default=None)
    evidence_valid_until = serializers.DateField(
        source="evidence.valid_until", read_only=True, default=None,
    )
    evidence_file_path = serializers.CharField(
        source="evidence.file_path", read_only=True, default=None,
    )
    # Ruoli critici e organo di gestione: chi ha partecipato, scelto fra i
    # titolari di nomine e i componenti degli organi di governo del sito.
    participant_users = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), many=True, write_only=True, required=False,
    )
    participant_members = serializers.PrimaryKeyRelatedField(
        queryset=CommitteeMember.objects.all(), many=True, write_only=True, required=False,
    )
    participants_detail = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = ["id", "course", "course_title", "course_kind", "plan_item", "plant", "plant_code",
                  "held_on", "audiences", "target_count", "trained_count", "sent_count",
                  "clicked_count", "reported_count", "evidence", "evidence_valid_until",
                  "evidence_file_path", "legacy", "notes", "file",
                  "participant_users", "participant_members", "participants_detail",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM + ["evidence", "legacy"]

    def get_participants_detail(self, obj):
        return [participant_row(p) for p in obj.participants.all()]


def participant_row(p) -> dict:
    member = p.committee_member
    if member is not None:
        name = member.full_name
    elif p.user is not None:
        name = p.user.get_full_name().strip() or p.user.email or p.user.username
    else:
        name = ""
    return {
        "id": str(p.pk),
        "name": name,
        "roles": p.roles,
        "committee": member.committee.name if member is not None else None,
        "user_id": str(p.user_id) if p.user_id else None,
        "member_id": str(p.committee_member_id) if p.committee_member_id else None,
    }
