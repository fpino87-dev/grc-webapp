from rest_framework import serializers

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
    class Meta:
        model = ChecklistTemplateItem
        fields = ["id", "order", "text", "is_mandatory"]


class ChecklistTemplateSerializer(serializers.ModelSerializer):
    # Gestione inline degli item: il client invia l'intera lista, qui la
    # sincronizziamo (create/update/delete) in modo transazionale.
    items = ChecklistTemplateItemSerializer(many=True, required=False)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    runs_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "description", "frequency", "plant", "plant_name",
            "is_active", "items", "runs_count", "created_at", "updated_at",
        ]

    def get_runs_count(self, obj):
        return obj.runs.count()

    def _sync_items(self, template, items_data):
        template.items.all().delete()
        ChecklistTemplateItem.objects.bulk_create([
            ChecklistTemplateItem(
                template=template,
                order=item.get("order", idx),
                text=item["text"],
                is_mandatory=item.get("is_mandatory", True),
            )
            for idx, item in enumerate(items_data)
        ])

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        template = ChecklistTemplate.objects.create(**validated_data)
        self._sync_items(template, items_data)
        return template

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            self._sync_items(instance, items_data)
        return instance


class ChecklistRunItemSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="template_item.text", read_only=True)
    is_mandatory = serializers.BooleanField(
        source="template_item.is_mandatory", read_only=True
    )
    order = serializers.IntegerField(source="template_item.order", read_only=True)

    class Meta:
        model = ChecklistRunItem
        fields = [
            "id", "template_item", "text", "is_mandatory", "order",
            "checked", "note", "checked_at", "checked_by",
        ]
        read_only_fields = ["checked_at", "checked_by"]


class ChecklistRunSerializer(serializers.ModelSerializer):
    items = ChecklistRunItemSerializer(many=True, read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    progress_total = serializers.SerializerMethodField(read_only=True)
    progress_done = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChecklistRun
        fields = [
            "id", "template", "template_name", "plant", "plant_name",
            "assigned_to", "due_date", "completed_at", "completed_by",
            "status", "items", "progress_total", "progress_done", "created_at",
        ]
        read_only_fields = ["completed_at", "completed_by", "created_at"]

    def get_progress_total(self, obj):
        return obj.items.count()

    def get_progress_done(self, obj):
        return obj.items.filter(checked=True).count()
