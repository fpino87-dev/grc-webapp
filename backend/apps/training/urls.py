from rest_framework.routers import DefaultRouter

from .views import PhishingSimulationViewSet, TrainingCourseViewSet, TrainingEnrollmentViewSet

router = DefaultRouter()
router.register("courses", TrainingCourseViewSet, basename="training-course")
router.register("enrollments", TrainingEnrollmentViewSet, basename="training-enrollment")
router.register("phishing", PhishingSimulationViewSet, basename="phishing-simulation")

urlpatterns = router.urls

