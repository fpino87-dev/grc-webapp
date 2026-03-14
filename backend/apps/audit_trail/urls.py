from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuditIntegrityView, AuditLogViewSet

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls + [
    path("verify-integrity/", AuditIntegrityView.as_view(), name="audit-verify-integrity"),
]

