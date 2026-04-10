from rest_framework.routers import DefaultRouter

from .views import AssetDependencyViewSet, AssetITViewSet, AssetOTViewSet, AssetSWViewSet, NetworkZoneViewSet

router = DefaultRouter()
router.register("network-zones", NetworkZoneViewSet, basename="network-zone")
router.register("it", AssetITViewSet, basename="asset-it")
router.register("ot", AssetOTViewSet, basename="asset-ot")
router.register("sw", AssetSWViewSet, basename="asset-sw")
router.register("dependencies", AssetDependencyViewSet, basename="asset-dependency")

urlpatterns = router.urls
