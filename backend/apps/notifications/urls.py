from rest_framework.routers import DefaultRouter

from .views import EmailConfigurationViewSet, NotificationSubscriptionViewSet

router = DefaultRouter()
router.register(
    "subscriptions",
    NotificationSubscriptionViewSet,
    basename="notification-subscription",
)
router.register(
    "email-config",
    EmailConfigurationViewSet,
    basename="email-config",
)

urlpatterns = router.urls

