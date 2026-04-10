from rest_framework import serializers
from .models import BcpPlan, BcpTest


class BcpTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BcpTest
        fields = "__all__"


class BcpPlanSerializer(serializers.ModelSerializer):
    tests = BcpTestSerializer(many=True, read_only=True)

    class Meta:
        model = BcpPlan
        fields = "__all__"
