from rest_framework import serializers

from .models import Task, TaskComment


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
