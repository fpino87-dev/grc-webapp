from rest_framework import serializers

from .models import (
    TrainingAudience,
    TrainingCourse,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)


class TrainingCourseSerializer(serializers.ModelSerializer):
    # Controlli che l'erogazione del corso dimostra, leggibili senza un'altra
    # chiamata: codice, framework e titolo.
    controls_detail = serializers.SerializerMethodField()

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
            "deadline",
            "kind",
            "audience_kind",
            "validity_months",
            "controls",
            "controls_detail",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]

    def get_controls_detail(self, obj):
        lang = getattr(self.context.get("request"), "LANGUAGE_CODE", "it")
        return [control_option(c, lang) for c in obj.controls.all()]


def control_option(control, lang="it") -> dict:
    return {
        "id": str(control.pk),
        "external_id": control.external_id,
        "framework_code": control.framework.code,
        "title": control.get_title(lang),
    }


_SYSTEM = ["id", "created_at", "updated_at", "created_by"]


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

    class Meta:
        model = TrainingSession
        fields = ["id", "course", "course_title", "course_kind", "plan_item", "plant", "plant_code",
                  "held_on", "audiences", "target_count", "trained_count", "sent_count",
                  "clicked_count", "reported_count", "evidence", "evidence_valid_until",
                  "evidence_file_path", "legacy", "notes", "file",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM + ["evidence", "legacy"]
