from rest_framework import viewsets

from .models import Control, ControlDomain, ControlInstance, Framework
from .serializers import (
    ControlDomainSerializer,
    ControlInstanceSerializer,
    ControlSerializer,
    FrameworkSerializer,
)


class FrameworkViewSet(viewsets.ModelViewSet):
    queryset = Framework.objects.all()
    serializer_class = FrameworkSerializer


class ControlDomainViewSet(viewsets.ModelViewSet):
    queryset = ControlDomain.objects.select_related("framework")
    serializer_class = ControlDomainSerializer


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.select_related("framework", "domain")
    serializer_class = ControlSerializer


class ControlInstanceViewSet(viewsets.ModelViewSet):
    queryset = ControlInstance.objects.select_related("plant", "control")
    serializer_class = ControlInstanceSerializer

