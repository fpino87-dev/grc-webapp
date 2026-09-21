from rest_framework.routers import DefaultRouter

from .views import (
    TrainingAudienceViewSet,
    TrainingCourseViewSet,
    TrainingPlanItemViewSet,
    TrainingPlanViewSet,
    TrainingSessionViewSet,
)

router = DefaultRouter()
router.register("courses", TrainingCourseViewSet, basename="training-course")
router.register("audiences", TrainingAudienceViewSet, basename="training-audience")
router.register("plans", TrainingPlanViewSet, basename="training-plan")
router.register("plan-items", TrainingPlanItemViewSet, basename="training-plan-item")
router.register("sessions", TrainingSessionViewSet, basename="training-session")

urlpatterns = router.urls

