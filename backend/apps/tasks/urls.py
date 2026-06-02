from rest_framework.routers import DefaultRouter

from .views import (
    ChecklistRunViewSet,
    ChecklistTemplateViewSet,
    KPIDefinitionViewSet,
    OperationalKpiSnapshotViewSet,
    TaskCommentViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-comments", TaskCommentViewSet, basename="task-comment")
router.register("checklist-templates", ChecklistTemplateViewSet, basename="checklist-template")
router.register("checklist-runs", ChecklistRunViewSet, basename="checklist-run")
router.register("kpi-definitions", KPIDefinitionViewSet, basename="kpi-definition")
router.register("kpi-snapshots", OperationalKpiSnapshotViewSet, basename="kpi-snapshot")

urlpatterns = router.urls
