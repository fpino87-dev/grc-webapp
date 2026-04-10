from rest_framework.routers import DefaultRouter

from .views import TaskCommentViewSet, TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-comments", TaskCommentViewSet, basename="task-comment")

urlpatterns = router.urls
