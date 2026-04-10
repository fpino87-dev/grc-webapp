from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExternalAuditorTokenViewSet,
    ResetTestDbView,
    RoleCompetencyRequirementViewSet,
    UserCompetencyViewSet,
    UserPlantAccessViewSet,
)
from .user_views import UserViewSet
from .mfa_views import MfaStatusView, MfaSetupView, MfaDisableView

router = DefaultRouter()
router.register("plant-access", UserPlantAccessViewSet, basename="plant-access")
router.register("auditor-tokens", ExternalAuditorTokenViewSet, basename="auditor-token")
router.register("users", UserViewSet, basename="user")
router.register("competency-requirements", RoleCompetencyRequirementViewSet, basename="competency-requirement")
router.register("user-competencies", UserCompetencyViewSet, basename="user-competency")

urlpatterns = router.urls + [
    path("reset-test-db/",       ResetTestDbView.as_view(),  name="reset-test-db"),
    path("mfa/status/",          MfaStatusView.as_view(),    name="mfa-status"),
    path("mfa/setup/",           MfaSetupView.as_view(),     name="mfa-setup"),
    path("mfa/device/",          MfaDisableView.as_view(),   name="mfa-disable"),
]
