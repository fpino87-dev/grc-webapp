from rest_framework import serializers
from .models import Supplier, SupplierAssessment


class SupplierAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAssessment
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
