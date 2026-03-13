from rest_framework import serializers

from .models import Control, ControlDomain, ControlInstance, Framework


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = "__all__"


class ControlDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlDomain
        fields = "__all__"


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = "__all__"


class ControlInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlInstance
        fields = "__all__"

