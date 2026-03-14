from rest_framework.routers import DefaultRouter

from .views import NotificationSubscriptionViewSet

router = DefaultRouter()
router.register("subscriptions", NotificationSubscriptionViewSet, basename="notification-subscription")

urlpatterns = router.urls

