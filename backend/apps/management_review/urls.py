from rest_framework.routers import DefaultRouter
from .views import ManagementReviewViewSet, ReviewActionViewSet

router = DefaultRouter()
router.register("reviews", ManagementReviewViewSet, basename="management-review")
router.register("review-actions", ReviewActionViewSet, basename="review-action")

urlpatterns = router.urls
