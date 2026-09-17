from rest_framework.routers import DefaultRouter
from .views import ManagementReviewViewSet, ReviewActionViewSet, ReviewAgendaItemViewSet

router = DefaultRouter()
router.register("reviews", ManagementReviewViewSet, basename="management-review")
router.register("review-actions", ReviewActionViewSet, basename="review-action")
router.register("agenda-items", ReviewAgendaItemViewSet, basename="review-agenda-item")

urlpatterns = router.urls
