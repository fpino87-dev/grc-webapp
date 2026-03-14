from rest_framework.routers import DefaultRouter

from .views import ExternalAuditorTokenViewSet, UserPlantAccessViewSet
from .user_views import UserViewSet

router = DefaultRouter()
router.register("plant-access", UserPlantAccessViewSet, basename="plant-access")
router.register("auditor-tokens", ExternalAuditorTokenViewSet, basename="auditor-token")
router.register("users", UserViewSet, basename="user")

urlpatterns = router.urls
