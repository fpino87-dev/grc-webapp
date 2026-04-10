from rest_framework.routers import DefaultRouter
from .views import BcpPlanViewSet, BcpTestViewSet

router = DefaultRouter()
router.register("plans", BcpPlanViewSet, basename="bcp-plan")
router.register("tests", BcpTestViewSet, basename="bcp-test")

urlpatterns = router.urls
