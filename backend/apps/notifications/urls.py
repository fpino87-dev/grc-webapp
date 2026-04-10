from rest_framework.routers import DefaultRouter

from .views import (
    EmailConfigurationViewSet,
    NotificationRoleProfileViewSet,
    NotificationRuleViewSet,
    NotificationSubscriptionViewSet,
)

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
router.register(
    "rules",
    NotificationRuleViewSet,
    basename="notification-rule",
)
router.register(
    "role-profiles",
    NotificationRoleProfileViewSet,
    basename="notification-role-profile",
)

urlpatterns = router.urls
