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

router = DefaultRouter()
router.register("plant-access", UserPlantAccessViewSet, basename="plant-access")
router.register("auditor-tokens", ExternalAuditorTokenViewSet, basename="auditor-token")
router.register("users", UserViewSet, basename="user")
router.register("competency-requirements", RoleCompetencyRequirementViewSet, basename="competency-requirement")
router.register("user-competencies", UserCompetencyViewSet, basename="user-competency")

urlpatterns = router.urls + [
    path("reset-test-db/", ResetTestDbView.as_view(), name="reset-test-db"),
]
