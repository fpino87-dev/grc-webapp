from rest_framework import serializers
from .models import LessonLearned


class LessonLearnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonLearned
        fields = "__all__"
