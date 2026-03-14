from rest_framework.routers import DefaultRouter

from .views import BusinessUnitViewSet, PlantFrameworkViewSet, PlantViewSet

router = DefaultRouter()
router.register("business-units", BusinessUnitViewSet, basename="business-unit")
router.register("plants", PlantViewSet, basename="plant")
router.register("plant-frameworks", PlantFrameworkViewSet, basename="plant-framework")

urlpatterns = router.urls

