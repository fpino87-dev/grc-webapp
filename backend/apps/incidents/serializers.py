from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import Incident, IncidentNotification, NIS2Configuration, NIS2Notification, RCA


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = "__all__"
        # I campi di classificazione NIS2 e di chiusura sono GOVERNATI: vengono
        # scritti solo dal motore (`classify_significance`/`set_nis2_deadlines`) e
        # dalle azioni dedicate (close, confirm_nis2, classify-significance), mai
        # da una PATCH diretta del client. Senza questo lock un utente con
        # permesso di scrittura potrebbe declassare un incidente significativo,
        # azzerarne le scadenze o chiuderlo aggirando il gate RCA — falsando il
        # dossier ispettivo NIS2.
        read_only_fields = [
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "closed_at",
            "closed_by",
            "axis_operational",
            "axis_economic",
            "axis_people",
            "axis_confidentiality",
            "axis_reputational",
            "axis_recurrence",
            "pta_nis2",
            "ptnr_nis2",
            "pt_gdpr",
            "acn_is_category",
            "requires_csirt_notification",
            "requires_gdpr_notification",
            "is_significant",
            "significance_override",
            "significance_override_reason",
            "early_warning_deadline",
            "formal_notification_deadline",
            "final_report_deadline",
        ]

    def validate(self, attrs):
        # La chiusura passa solo dall'azione `close` (richiede RCA approvato e
        # genera PDCA/Lesson/audit). Blocca la transizione aperto/in_analisi →
        # chiuso via serializer, consentendo comunque di salvare modifiche su un
        # incidente già chiuso.
        new_status = attrs.get("status")
        if new_status == "chiuso" and getattr(self.instance, "status", None) != "chiuso":
            raise serializers.ValidationError(
                {
                    "status": _(
                        "La chiusura dell'incidente avviene solo tramite l'azione "
                        "dedicata, previo RCA approvato."
                    )
                }
            )
        return attrs


class IncidentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentNotification
        fields = "__all__"


class RCASerializer(serializers.ModelSerializer):
    class Meta:
        model = RCA
        fields = "__all__"


class NIS2NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NIS2Notification
        fields = "__all__"


class NIS2ConfigurationSerializer(serializers.ModelSerializer):
    """Solo parametri di calcolo significatività — anagrafica NIS2 è sul Plant (M01)."""

    class Meta:
        model = NIS2Configuration
        fields = [
            "id",
            "plant",
            "threshold_users",
            "threshold_hours",
            "threshold_financial",
            "multiplier_medium",
            "multiplier_high",
            "recurrence_window_days",
            "recurrence_score_bonus",
            "ptnr_threshold",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

