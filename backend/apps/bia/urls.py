from rest_framework.routers import DefaultRouter

from .views import CriticalProcessViewSet, RiskDecisionViewSet, TreatmentOptionViewSet

router = DefaultRouter()
router.register("processes", CriticalProcessViewSet, basename="critical-process")
router.register("treatment-options", TreatmentOptionViewSet, basename="treatment-option")
router.register("risk-decisions", RiskDecisionViewSet, basename="risk-decision")

urlpatterns = router.urls
