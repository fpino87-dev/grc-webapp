from rest_framework.routers import DefaultRouter

from .views import (
    BusinessObjectiveViewSet,
    InformationClassViewSet,
    RiskAcceptanceViewSet,
    RiskAssessmentCycleViewSet,
    RiskAssessmentViewSet,
    RiskExistingMeasureViewSet,
    RiskGovernancePolicyViewSet,
    RiskLocalImpactReportViewSet,
    RiskMitigationPlanViewSet,
    ThreatCatalogViewSet,
)

router = DefaultRouter()
router.register("assessments", RiskAssessmentViewSet, basename="risk-assessment")
router.register("existing-measures", RiskExistingMeasureViewSet, basename="risk-existing-measure")
router.register("mitigation-plans", RiskMitigationPlanViewSet, basename="risk-mitigation-plan")
router.register("acceptances", RiskAcceptanceViewSet, basename="risk-acceptance")
router.register("local-impact-reports", RiskLocalImpactReportViewSet, basename="risk-local-impact")
router.register("threats", ThreatCatalogViewSet, basename="risk-threat")
router.register("information-classes", InformationClassViewSet, basename="risk-information-class")
router.register("business-objectives", BusinessObjectiveViewSet, basename="risk-business-objective")
router.register("governance-policies", RiskGovernancePolicyViewSet, basename="risk-governance-policy")
router.register("cycles", RiskAssessmentCycleViewSet, basename="risk-cycle")

urlpatterns = router.urls
