from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, SupplierAssessmentViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("assessments", SupplierAssessmentViewSet, basename="supplier-assessment")

urlpatterns = router.urls
