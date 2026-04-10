from rest_framework.routers import DefaultRouter
from .views import LessonLearnedViewSet

router = DefaultRouter()
router.register("lessons", LessonLearnedViewSet, basename="lesson-learned")

urlpatterns = router.urls
