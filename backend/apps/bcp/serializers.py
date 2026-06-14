from rest_framework import serializers
from .models import BcpPlan, BcpTest


class BcpTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BcpTest
        fields = "__all__"
        # Il test è registrato dall'azione record_test (che imposta esecutore,
        # data e crea PDCA su esito fallito/parziale): chi l'ha condotto non è
        # impostabile dal client.
        read_only_fields = [
            "id", "conducted_by", "created_by", "created_at", "updated_at", "deleted_at",
        ]


class BcpPlanSerializer(serializers.ModelSerializer):
    tests = BcpTestSerializer(many=True, read_only=True)

    class Meta:
        model = BcpPlan
        fields = "__all__"
        # L'approvazione del piano BCP passa SOLO dall'azione `approve`, che
        # verifica l'autorizzazione CISO/Compliance sul sito. Senza questo lock
        # un ruolo con permesso di scrittura (es. plant_manager) potrebbe
        # auto-approvare un piano con una PATCH diretta, impostando stato,
        # approvatore e data e scavalcando il controllo di autorizzazione.
        # `last_test_date`/`next_test_date` sono calcolati da record_test.
        read_only_fields = [
            "id",
            "status",
            "approved_by",
            "approved_at",
            "last_test_date",
            "next_test_date",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
