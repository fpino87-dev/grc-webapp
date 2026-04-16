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
    latest_questionnaire_status = serializers.SerializerMethodField(read_only=True)
    concentration_threshold = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Supplier
        fields = "__all__"

    def get_latest_questionnaire_status(self, obj):
        q = obj.questionnaires.order_by("-sent_at").first()
        return q.status if q else None

    def get_concentration_threshold(self, obj):
        return obj.concentration_threshold

    def validate_vat_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Il Codice Fiscale / P.IVA è obbligatorio.")
        return value.strip()

    def validate(self, data):
        nis2_relevant = data.get("nis2_relevant", getattr(self.instance, "nis2_relevant", False))
        criterion = data.get("nis2_relevance_criterion", getattr(self.instance, "nis2_relevance_criterion", ""))
        if nis2_relevant and not criterion:
            raise serializers.ValidationError(
                {"nis2_relevance_criterion": "Il criterio di rilevanza NIS2 è obbligatorio quando il fornitore è marcato come NIS2 rilevante."}
            )
        return data


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
