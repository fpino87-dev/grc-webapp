from io import StringIO

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ExternalAuditorToken, RoleCompetencyRequirement, UserCompetency, UserPlantAccess
from .serializers import (
    ExternalAuditorTokenSerializer,
    RoleCompetencyRequirementSerializer,
    UserCompetencySerializer,
    UserPlantAccessSerializer,
)


class ResetTestDbView(APIView):
    """
    SOLO PER TESTING — Reset completo DB.
    Richiede: is_superuser=True + header X-Confirm-Reset: RESET-CONFIRMED
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {"error": "Solo il superuser può eseguire questa operazione"},
                status=403,
            )
        confirm = request.headers.get("X-Confirm-Reset", "")
        if confirm != "RESET-CONFIRMED":
            return Response(
                {"error": "Header X-Confirm-Reset: RESET-CONFIRMED richiesto"},
                status=400,
            )

        from django.core.management import call_command

        out = StringIO()
        try:
            call_command("reset_test_db", "--confirm", stdout=out)
            return Response({
                "status": "ok",
                "message": "Reset completato",
                "detail": out.getvalue(),
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UserPlantAccessViewSet(viewsets.ModelViewSet):
    queryset = UserPlantAccess.objects.select_related("scope_bu")
    serializer_class = UserPlantAccessSerializer


class ExternalAuditorTokenViewSet(viewsets.ModelViewSet):
    queryset = ExternalAuditorToken.objects.select_related("plant", "user")
    serializer_class = ExternalAuditorTokenSerializer


class RoleCompetencyRequirementViewSet(viewsets.ModelViewSet):
    queryset = RoleCompetencyRequirement.objects.all()
    serializer_class = RoleCompetencyRequirementSerializer
    filterset_fields = ["grc_role", "mandatory"]


class UserCompetencyViewSet(viewsets.ModelViewSet):
    queryset = UserCompetency.objects.select_related("user", "verified_by", "evidence")
    serializer_class = UserCompetencySerializer
    filterset_fields = ["user"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="gap-analysis")
    def gap_analysis(self, request):
        from .services import competency_gap_analysis
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = request.query_params.get("user", request.user.pk)
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"error": "Utente non trovato"}, status=404)
        return Response(competency_gap_analysis(user))

