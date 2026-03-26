from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import UserPlantAccess, GrcRole
from .permissions import IsGrcSuperAdmin
from .services import deactivate_grc_user

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    grc_role = serializers.SerializerMethodField()
    plant_access = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "is_active", "is_staff", "is_superuser", "date_joined",
                  "grc_role", "plant_access"]
        read_only_fields = ["id", "date_joined", "grc_role", "plant_access"]

    def get_grc_role(self, obj):
        if obj.is_superuser:
            return "super_admin"
        access = UserPlantAccess.objects.filter(user=obj).first()
        return access.role if access else None

    def get_plant_access(self, obj):
        accesses = UserPlantAccess.objects.filter(user=obj).select_related("scope_bu").prefetch_related("scope_plants")
        return [{"id": str(a.id), "role": a.role, "scope_type": a.scope_type} for a in accesses]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # esponiamo solo un sottoinsieme dei ruoli GRC per la UI
    EXPOSED_ROLES = [
        (GrcRole.SUPER_ADMIN, "Super Admin"),
        (GrcRole.PLANT_MANAGER, "Plant Admin"),
        (GrcRole.CONTROL_OWNER, "User"),
    ]
    grc_role = serializers.ChoiceField(choices=[r[0] for r in EXPOSED_ROLES], required=False, write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "is_staff", "grc_role"]

    def create(self, validated_data):
        grc_role = validated_data.pop("grc_role", None)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if grc_role:
            UserPlantAccess.objects.create(user=user, role=grc_role, scope_type="org")
        return user


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8)


class AssignRoleSerializer(serializers.Serializer):
    # stessi ruoli esposti in creazione
    EXPOSED_ROLES = UserCreateSerializer.EXPOSED_ROLES
    role = serializers.ChoiceField(choices=[r[0] for r in EXPOSED_ROLES])
    scope_type = serializers.ChoiceField(
        choices=["org", "bu", "plant_list", "single_plant"],
        default="org"
    )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_active=True).order_by("username")
    filterset_fields = ["is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["me", "list_roles"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsGrcSuperAdmin()]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            deactivate_grc_user(user, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save()
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def assign_role(self, request, pk=None):
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        scope_type = serializer.validated_data["scope_type"]
        # Replace existing org-level access
        UserPlantAccess.objects.filter(user=user, scope_type="org").delete()
        UserPlantAccess.objects.create(user=user, role=role, scope_type=scope_type)
        return Response({"ok": True, "role": role})

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response({"is_active": user.is_active})

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def list_roles(self, request):
        # restituiamo solo il sottoinsieme di ruoli GRC usati per la gestione utenti
        return Response(
            [{"value": value, "label": label} for value, label in UserCreateSerializer.EXPOSED_ROLES]
        )
