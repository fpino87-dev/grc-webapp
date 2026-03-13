from rest_framework import viewsets

from .models import BusinessUnit, Plant
from .serializers import BusinessUnitSerializer, PlantSerializer


class BusinessUnitViewSet(viewsets.ModelViewSet):
    queryset = BusinessUnit.objects.all()
    serializer_class = BusinessUnitSerializer


class PlantViewSet(viewsets.ModelViewSet):
    queryset = Plant.objects.select_related("bu", "parent_plant")
    serializer_class = PlantSerializer

