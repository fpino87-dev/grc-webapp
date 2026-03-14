from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ControlDomainViewSet,
    ControlInstanceViewSet,
    ControlViewSet,
    FrameworkViewSet,
    GapAnalysisView,
)

router = DefaultRouter()
router.register("frameworks", FrameworkViewSet, basename="framework")
router.register("domains", ControlDomainViewSet, basename="control-domain")
router.register("controls", ControlViewSet, basename="control")
router.register("instances", ControlInstanceViewSet, basename="control-instance")

urlpatterns = router.urls + [
    path("gap-analysis/", GapAnalysisView.as_view(), name="gap-analysis"),
]

