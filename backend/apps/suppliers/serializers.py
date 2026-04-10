from rest_framework import serializers
from .models import Supplier, SupplierAssessment, QuestionnaireTemplate, SupplierQuestionnaire


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


class QuestionnaireTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireTemplate
        fields = "__all__"


class SupplierQuestionnaireSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    sent_by_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplierQuestionnaire
        fields = "__all__"

    def get_sent_by_display(self, obj):
        if not obj.sent_by:
            return None
        return (
            f"{obj.sent_by.first_name} {obj.sent_by.last_name}".strip()
            or obj.sent_by.email
        )
