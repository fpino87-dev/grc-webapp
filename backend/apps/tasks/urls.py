from rest_framework.routers import DefaultRouter

from .views import (
    ChecklistRunViewSet,
    ChecklistTemplateViewSet,
    TaskCommentViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-comments", TaskCommentViewSet, basename="task-comment")
router.register("checklist-templates", ChecklistTemplateViewSet, basename="checklist-template")
router.register("checklist-runs", ChecklistRunViewSet, basename="checklist-run")

urlpatterns = router.urls
