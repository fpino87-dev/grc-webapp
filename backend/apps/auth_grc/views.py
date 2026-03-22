from io import StringIO

from django.conf import settings
from django.utils.translation import gettext as _
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
        if not settings.DEBUG:
            return Response(
                {"error": _("Endpoint disponibile solo in ambiente di test (DEBUG=True).")},
                status=403,
            )
        if not request.user.is_superuser:
            return Response(
                {"error": _("Solo il superuser può eseguire questa operazione")},
                status=403,
            )
        confirm = request.headers.get("X-Confirm-Reset", "")
        if confirm != "RESET-CONFIRMED":
            return Response(
                {"error": _("Header X-Confirm-Reset: RESET-CONFIRMED richiesto")},
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

    @action(
        detail=False,
        methods=["post"],
        url_path=r"users/(?P<user_pk>[^/.]+)/anonymize",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def anonymize_user(self, request, user_pk=None):
        from django.contrib.auth import get_user_model
        from .services import anonymize_user
        User = get_user_model()
        user = User.objects.filter(pk=user_pk).first()
        if not user:
            return Response({"error": _("Utente non trovato")}, status=404)
        reason = request.data.get("reason", "")
        if not reason or len(reason.strip()) < 10:
            return Response({
                "error": _("Motivazione obbligatoria (min 10 caratteri) per richiesta GDPR Art. 17")
            }, status=400)
        anonymize_user(user, request.user)
        return Response({"ok": True, "message": _("Utente anonimizzato (GDPR Art. 17)")})


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
            return Response({"error": _("Utente non trovato")}, status=404)
        return Response(competency_gap_analysis(user))

