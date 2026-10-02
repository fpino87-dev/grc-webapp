from rest_framework.routers import DefaultRouter

from .views import CriticalProcessViewSet

router = DefaultRouter()
router.register("processes", CriticalProcessViewSet, basename="critical-process")

urlpatterns = router.urls
