from rest_framework.routers import DefaultRouter
from .views import (
    AuditFindingViewSet, AuditGroupViewSet, AuditPrepViewSet, AuditProgramViewSet, EvidenceItemViewSet,
)

router = DefaultRouter()
router.register("audit-preps", AuditPrepViewSet, basename="audit-prep")
router.register("audit-groups", AuditGroupViewSet, basename="audit-group")
router.register("evidence-items", EvidenceItemViewSet, basename="evidence-item")
router.register("findings", AuditFindingViewSet, basename="finding")
router.register("programs", AuditProgramViewSet, basename="audit-program")

urlpatterns = router.urls
