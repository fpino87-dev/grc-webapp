from rest_framework import serializers

from .models import PhishingSimulation, TrainingCourse, TrainingEnrollment


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
