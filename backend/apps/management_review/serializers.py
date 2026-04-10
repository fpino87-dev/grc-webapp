from rest_framework import serializers
from .models import ManagementReview, ReviewAction


class ReviewActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewAction
        fields = "__all__"


class ManagementReviewSerializer(serializers.ModelSerializer):
    actions = ReviewActionSerializer(many=True, read_only=True)

    class Meta:
        model = ManagementReview
        fields = "__all__"
