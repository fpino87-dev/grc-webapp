from rest_framework import serializers
from .models import LessonLearned


class LessonLearnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonLearned
        fields = "__all__"
        # Il ciclo di vita (bozza → validato → propagato) è governato dalle
        # azioni dedicate `validate`/`propagate` (SoD + audit): non deve essere
        # alterabile con una PATCH diretta, che permetterebbe di marcare una
        # lezione "validato" falsificandone validatore/data e saltando l'audit.
        read_only_fields = [
            "id",
            "status",
            "validated_by",
            "validated_at",
            "propagated_to_plants",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "source_module",
            "source_id",
        ]
