from rest_framework import serializers
from .models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
    QuestionnaireTemplate,
    SupplierQuestionnaire,
)


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
        read_only_fields = ["internal_risk_level", "risk_adj", "risk_adj_updated_at"]

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


class SupplierInternalEvaluationSerializer(serializers.ModelSerializer):
    evaluated_by_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupplierInternalEvaluation
        fields = [
            "id",
            "supplier",
            "score_impatto",
            "score_accesso",
            "score_dati",
            "score_dipendenza",
            "score_integrazione",
            "score_compliance",
            "weighted_score",
            "risk_class",
            "weights_snapshot",
            "thresholds_snapshot",
            "is_current",
            "evaluated_by",
            "evaluated_by_display",
            "evaluated_at",
            "notes",
        ]
        read_only_fields = [
            "id", "weighted_score", "risk_class", "weights_snapshot",
            "thresholds_snapshot", "is_current", "evaluated_by", "evaluated_at",
        ]

    def get_evaluated_by_display(self, obj):
        if not obj.evaluated_by:
            return None
        return (
            f"{obj.evaluated_by.first_name} {obj.evaluated_by.last_name}".strip()
            or obj.evaluated_by.email
        )


class SupplierEvaluationConfigSerializer(serializers.ModelSerializer):
    PARAMETER_KEYS = {"impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"}
    THRESHOLD_KEYS = {"medio", "alto", "critico"}

    class Meta:
        model = SupplierEvaluationConfig
        fields = [
            "weights",
            "parameter_labels",
            "risk_thresholds",
            "questionnaire_validity_months",
            "assessment_validity_months",
            "nis2_concentration_bump",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_weights(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Deve essere un oggetto chiave→peso.")
        if set(value.keys()) != self.PARAMETER_KEYS:
            raise serializers.ValidationError(
                f"Chiavi obbligatorie: {sorted(self.PARAMETER_KEYS)}."
            )
        try:
            nums = {k: float(v) for k, v in value.items()}
        except (TypeError, ValueError):
            raise serializers.ValidationError("I pesi devono essere numerici.")
        if any(v < 0 for v in nums.values()):
            raise serializers.ValidationError("I pesi non possono essere negativi.")
        total = sum(nums.values())
        if abs(total - 1.0) > 0.001:
            raise serializers.ValidationError(
                f"La somma dei pesi deve essere 1.00 (attuale: {total:.3f})."
            )
        return nums

    def validate_parameter_labels(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Deve essere un oggetto chiave→{name, levels}.")
        if set(value.keys()) != self.PARAMETER_KEYS:
            raise serializers.ValidationError(
                f"Chiavi obbligatorie: {sorted(self.PARAMETER_KEYS)}."
            )
        for key, payload in value.items():
            if not isinstance(payload, dict) or "name" not in payload or "levels" not in payload:
                raise serializers.ValidationError(
                    f"'{key}': struttura attesa {{name, levels}}."
                )
            levels = payload["levels"]
            if not isinstance(levels, list) or len(levels) != 5:
                raise serializers.ValidationError(
                    f"'{key}': servono esattamente 5 label per i livelli 1–5."
                )
            if not all(isinstance(l, str) and l.strip() for l in levels):
                raise serializers.ValidationError(
                    f"'{key}': tutte le label devono essere stringhe non vuote."
                )
        return value

    def validate_risk_thresholds(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Deve essere un oggetto chiave→soglia.")
        if set(value.keys()) != self.THRESHOLD_KEYS:
            raise serializers.ValidationError(
                f"Chiavi obbligatorie: {sorted(self.THRESHOLD_KEYS)}."
            )
        try:
            nums = {k: float(v) for k, v in value.items()}
        except (TypeError, ValueError):
            raise serializers.ValidationError("Le soglie devono essere numeriche.")
        if not (1.0 <= nums["medio"] < nums["alto"] < nums["critico"] <= 5.0):
            raise serializers.ValidationError(
                "Le soglie devono essere crescenti e comprese tra 1.0 e 5.0 "
                "(medio < alto < critico)."
            )
        return nums

    def validate_questionnaire_validity_months(self, value):
        if value < 1 or value > 60:
            raise serializers.ValidationError("Validità in mesi tra 1 e 60.")
        return value

    def validate_assessment_validity_months(self, value):
        if value < 1 or value > 60:
            raise serializers.ValidationError("Validità in mesi tra 1 e 60.")
        return value


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
