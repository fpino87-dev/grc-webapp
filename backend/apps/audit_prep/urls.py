from rest_framework.routers import DefaultRouter
from .views import AuditFindingViewSet, AuditPrepViewSet, AuditProgramViewSet, EvidenceItemViewSet

router = DefaultRouter()
router.register("audit-preps", AuditPrepViewSet, basename="audit-prep")
router.register("evidence-items", EvidenceItemViewSet, basename="evidence-item")
router.register("findings", AuditFindingViewSet, basename="finding")
router.register("programs", AuditProgramViewSet, basename="audit-program")

urlpatterns = router.urls
