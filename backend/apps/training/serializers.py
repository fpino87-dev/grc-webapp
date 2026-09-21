from rest_framework import serializers

from .models import (
    PhishingSimulation,
    TrainingAudience,
    TrainingCourse,
    TrainingEnrollment,
    TrainingPlan,
    TrainingPlanItem,
    TrainingSession,
)


class TrainingCourseSerializer(serializers.ModelSerializer):
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
            "framework_refs",
            "plants",
            "deadline",
            "kind",
            "audience_kind",
            "validity_months",
            "controls",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingEnrollment
        fields = [
            "id",
            "course",
            "user",
            "status",
            "completed_at",
            "score",
            "passed",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class PhishingSimulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhishingSimulation
        fields = [
            "id",
            "kb4_simulation_id",
            "user",
            "plant",
            "result",
            "sent_at",
            "responded_at",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


_SYSTEM = ["id", "created_at", "updated_at", "created_by"]


class TrainingAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingAudience
        fields = ["id", "plant", "name", "headcount", "headcount_updated_at", "notes",
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
    document_status = serializers.CharField(source="document.status", read_only=True, default=None)

    class Meta:
        model = TrainingPlan
        fields = ["id", "plant", "year", "document", "document_status", "notes",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM
        validators = []


class TrainingSessionSerializer(serializers.ModelSerializer):
    # Il file arriva in multipart solo alla registrazione: diventa l'evidenza.
    file = serializers.FileField(write_only=True, required=False)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_kind = serializers.CharField(source="course.kind", read_only=True)
    evidence_valid_until = serializers.DateField(
        source="evidence.valid_until", read_only=True, default=None,
    )

    class Meta:
        model = TrainingSession
        fields = ["id", "course", "course_title", "course_kind", "plan_item", "plant", "held_on",
                  "audiences", "target_count", "trained_count", "sent_count", "clicked_count",
                  "reported_count", "evidence", "evidence_valid_until", "legacy", "notes", "file",
                  "created_at", "updated_at", "created_by"]
        read_only_fields = _SYSTEM + ["evidence", "legacy"]
