from rest_framework import viewsets

from .models import ExternalAuditorToken, UserPlantAccess
from .serializers import ExternalAuditorTokenSerializer, UserPlantAccessSerializer


class UserPlantAccessViewSet(viewsets.ModelViewSet):
    queryset = UserPlantAccess.objects.select_related("scope_bu")
    serializer_class = UserPlantAccessSerializer


class ExternalAuditorTokenViewSet(viewsets.ModelViewSet):
    queryset = ExternalAuditorToken.objects.select_related("plant", "user")
    serializer_class = ExternalAuditorTokenSerializer

