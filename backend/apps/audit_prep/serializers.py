from rest_framework import serializers
from .models import AuditPrep, EvidenceItem


class EvidenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceItem
        fields = "__all__"


class AuditPrepSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceItemSerializer(many=True, read_only=True)

    class Meta:
        model = AuditPrep
        fields = "__all__"
