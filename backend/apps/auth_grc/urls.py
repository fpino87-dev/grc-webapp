from rest_framework.routers import DefaultRouter

from .views import ExternalAuditorTokenViewSet, UserPlantAccessViewSet

router = DefaultRouter()
router.register("plant-access", UserPlantAccessViewSet, basename="plant-access")
router.register("auditor-tokens", ExternalAuditorTokenViewSet, basename="auditor-token")

urlpatterns = router.urls

