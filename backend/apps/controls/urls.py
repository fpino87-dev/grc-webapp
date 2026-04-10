from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ComplianceExportView,
    ControlDomainViewSet,
    ControlInstanceViewSet,
    ControlViewSet,
    FrameworkViewSet,
    GapAnalysisView,
)

# DefaultRouter genera un pattern <drf_format_suffix:format> per la api-root
# che intercetta URL come "export/" prima che raggiungano i path custom.
# Disabilitiamo la format suffix della root per evitare il conflitto.
router = DefaultRouter()
router.include_format_suffixes = False
router.register("frameworks", FrameworkViewSet, basename="framework")
router.register("domains", ControlDomainViewSet, basename="control-domain")
router.register("controls", ControlViewSet, basename="control")
router.register("instances", ControlInstanceViewSet, basename="control-instance")

urlpatterns = router.urls + [
    path("gap-analysis/", GapAnalysisView.as_view(), name="gap-analysis"),
    path("export/", ComplianceExportView.as_view(), name="compliance-export"),
]
