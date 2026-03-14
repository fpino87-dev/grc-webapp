from rest_framework.routers import DefaultRouter
from .views import AuditPrepViewSet, EvidenceItemViewSet

router = DefaultRouter()
router.register("audit-preps", AuditPrepViewSet, basename="audit-prep")
router.register("evidence-items", EvidenceItemViewSet, basename="evidence-item")

urlpatterns = router.urls
