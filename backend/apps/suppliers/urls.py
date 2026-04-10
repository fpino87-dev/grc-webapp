from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet,
    SupplierAssessmentViewSet,
    QuestionnaireTemplateViewSet,
    SupplierQuestionnaireViewSet,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("assessments", SupplierAssessmentViewSet, basename="supplier-assessment")
router.register("questionnaire-templates", QuestionnaireTemplateViewSet, basename="questionnaire-template")
router.register("questionnaires", SupplierQuestionnaireViewSet, basename="supplier-questionnaire")

urlpatterns = router.urls
