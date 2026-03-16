from rest_framework import serializers
from .models import Supplier, SupplierAssessment


class SupplierAssessmentSerializer(serializers.ModelSerializer):
    computed_risk_level = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplierAssessment
        fields = "__all__"

    def get_computed_risk_level(self, obj):
        return obj.computed_risk_level


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
