from rest_framework.routers import DefaultRouter

from .views import BusinessUnitViewSet, PlantViewSet

router = DefaultRouter()
router.register("business-units", BusinessUnitViewSet, basename="business-unit")
router.register("plants", PlantViewSet, basename="plant")

urlpatterns = router.urls

