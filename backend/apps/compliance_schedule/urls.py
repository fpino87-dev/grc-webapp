from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ComplianceSchedulePolicyViewSet,
    RequiredDocumentViewSet,
    ActivityScheduleView,
    RequiredDocumentsStatusView,
    RuleTypeCatalogueView,
)

router = DefaultRouter()
router.register("policies", ComplianceSchedulePolicyViewSet, basename="schedule-policy")
router.register("required-documents", RequiredDocumentViewSet, basename="required-document")

urlpatterns = [
    path("", include(router.urls)),
    path("activity/", ActivityScheduleView.as_view(), name="activity-schedule"),
    path("required-documents-status/", RequiredDocumentsStatusView.as_view(), name="required-documents-status"),
    path("rule-types/", RuleTypeCatalogueView.as_view(), name="rule-type-catalogue"),
]
