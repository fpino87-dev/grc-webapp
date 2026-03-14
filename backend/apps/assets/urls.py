from rest_framework.routers import DefaultRouter

from .views import AssetDependencyViewSet, AssetITViewSet, AssetOTViewSet, NetworkZoneViewSet

router = DefaultRouter()
router.register("network-zones", NetworkZoneViewSet, basename="network-zone")
router.register("it", AssetITViewSet, basename="asset-it")
router.register("ot", AssetOTViewSet, basename="asset-ot")
router.register("dependencies", AssetDependencyViewSet, basename="asset-dependency")

urlpatterns = router.urls
