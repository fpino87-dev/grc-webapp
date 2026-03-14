from rest_framework.routers import DefaultRouter

from .views import DocumentVersionViewSet, DocumentViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("document-versions", DocumentVersionViewSet, basename="document-version")

urlpatterns = router.urls
