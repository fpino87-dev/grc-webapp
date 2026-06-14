from rest_framework.routers import DefaultRouter

from .views import IncidentViewSet, NIS2ConfigurationViewSet, RCAViewSet

router = DefaultRouter()
router.register("incidents", IncidentViewSet, basename="incident")
router.register("nis2-configurations", NIS2ConfigurationViewSet, basename="nis2-configuration")
router.register("rca", RCAViewSet, basename="rca")

urlpatterns = router.urls

