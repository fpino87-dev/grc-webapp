from rest_framework.routers import DefaultRouter

from .views import PdcaCycleViewSet, PdcaPhaseViewSet

router = DefaultRouter()
router.register("cycles", PdcaCycleViewSet, basename="pdca-cycle")
router.register("phases", PdcaPhaseViewSet, basename="pdca-phase")

urlpatterns = router.urls

