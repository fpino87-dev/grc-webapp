from django.urls import path
from .views import ComplianceSummaryView, RiskSummaryView, IncidentSummaryView, DashboardSummaryView, OwnerReportView

urlpatterns = [
    path("compliance/", ComplianceSummaryView.as_view(), name="reporting-compliance"),
    path("risk/", RiskSummaryView.as_view(), name="reporting-risk"),
    path("incidents/", IncidentSummaryView.as_view(), name="reporting-incidents"),
    path("dashboard/", DashboardSummaryView.as_view(), name="reporting-dashboard"),
    path("owner-report/", OwnerReportView.as_view(), name="reporting-owner"),
]
