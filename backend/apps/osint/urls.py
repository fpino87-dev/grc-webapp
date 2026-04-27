from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    OsintAiView,
    OsintAlertViewSet,
    OsintDashboardView,
    OsintEntityViewSet,
    OsintFindingViewSet,
    OsintSettingsViewSet,
    OsintSubdomainViewSet,
)

router = DefaultRouter()
router.register("entities", OsintEntityViewSet, basename="osint-entity")
router.register("alerts", OsintAlertViewSet, basename="osint-alert")
router.register("findings", OsintFindingViewSet, basename="osint-finding")
router.register("subdomains", OsintSubdomainViewSet, basename="osint-subdomain")
router.register("dashboard", OsintDashboardView, basename="osint-dashboard")
router.register("settings", OsintSettingsViewSet, basename="osint-settings")
router.register("ai", OsintAiView, basename="osint-ai")

urlpatterns = router.urls + [
    # Endpoint singleton per settings (GET/PATCH)
    path("settings/", OsintSettingsViewSet.as_view({"get": "retrieve_settings", "patch": "update_settings"})),
]
