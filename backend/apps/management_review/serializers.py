from rest_framework import serializers
from .models import ManagementReview, ReviewAction


class ReviewActionSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return name or obj.owner.email

    class Meta:
        model = ReviewAction
        fields = "__all__"


class ManagementReviewSerializer(serializers.ModelSerializer):
    actions = ReviewActionSerializer(many=True, read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True, allow_null=True)

    class Meta:
        model = ManagementReview
        fields = "__all__"
