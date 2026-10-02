from rest_framework.routers import DefaultRouter

from .views import (
    InformationClassViewSet,
    RiskAppetitePolicyViewSet,
    RiskAssessmentCycleViewSet,
    RiskAssessmentViewSet,
    RiskDimensionViewSet,
    RiskGovernancePolicyViewSet,
    RiskMitigationPlanViewSet,
    ThreatCatalogViewSet,
)

router = DefaultRouter()
router.register("assessments", RiskAssessmentViewSet, basename="risk-assessment")
router.register("dimensions", RiskDimensionViewSet, basename="risk-dimension")
router.register("mitigation-plans", RiskMitigationPlanViewSet, basename="risk-mitigation-plan")
router.register("appetite-policies", RiskAppetitePolicyViewSet, basename="risk-appetite-policy")
router.register("threats", ThreatCatalogViewSet, basename="risk-threat")
router.register("information-classes", InformationClassViewSet, basename="risk-information-class")
router.register("governance-policies", RiskGovernancePolicyViewSet, basename="risk-governance-policy")
router.register("cycles", RiskAssessmentCycleViewSet, basename="risk-cycle")

urlpatterns = router.urls
