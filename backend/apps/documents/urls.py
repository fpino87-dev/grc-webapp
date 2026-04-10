from rest_framework.routers import DefaultRouter

from .views import DocumentVersionViewSet, DocumentViewSet, EvidenceViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("document-versions", DocumentVersionViewSet, basename="document-version")
router.register("evidences", EvidenceViewSet, basename="evidence")

urlpatterns = router.urls
