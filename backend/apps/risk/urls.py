from rest_framework.routers import DefaultRouter

from .views import (
    RiskAppetitePolicyViewSet,
    RiskAssessmentViewSet,
    RiskDimensionViewSet,
    RiskMitigationPlanViewSet,
)

router = DefaultRouter()
router.register("assessments", RiskAssessmentViewSet, basename="risk-assessment")
router.register("dimensions", RiskDimensionViewSet, basename="risk-dimension")
router.register("mitigation-plans", RiskMitigationPlanViewSet, basename="risk-mitigation-plan")
router.register("appetite-policies", RiskAppetitePolicyViewSet, basename="risk-appetite-policy")

urlpatterns = router.urls
