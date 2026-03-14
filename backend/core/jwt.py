from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class GrcTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["is_superuser"] = user.is_superuser
        # Get primary GRC role from UserPlantAccess
        from apps.auth_grc.models import UserPlantAccess
        access = UserPlantAccess.objects.filter(user=user).first()
        token["role"] = access.role if access else ("super_admin" if user.is_superuser else "user")
        return token


class GrcTokenObtainPairView(TokenObtainPairView):
    serializer_class = GrcTokenObtainPairSerializer
