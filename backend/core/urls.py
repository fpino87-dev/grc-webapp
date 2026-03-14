from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from core.jwt import GrcTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", GrcTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/v1/governance/", include("apps.governance.urls")),
    path("api/v1/plants/", include("apps.plants.urls")),
    path("api/v1/auth/", include("apps.auth_grc.urls")),
    path("api/v1/controls/", include("apps.controls.urls")),
    path("api/v1/assets/", include("apps.assets.urls")),
    path("api/v1/bia/", include("apps.bia.urls")),
    path("api/v1/risk/", include("apps.risk.urls")),
    path("api/v1/documents/", include("apps.documents.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/incidents/", include("apps.incidents.urls")),
    path("api/v1/audit-trail/", include("apps.audit_trail.urls")),
    path("api/v1/pdca/", include("apps.pdca.urls")),
    path("api/v1/lessons/", include("apps.lessons.urls")),
    path("api/v1/management-review/", include("apps.management_review.urls")),
    path("api/v1/suppliers/", include("apps.suppliers.urls")),
    path("api/v1/training/", include("apps.training.urls")),
    path("api/v1/bcp/", include("apps.bcp.urls")),
    path("api/v1/audit-prep/", include("apps.audit_prep.urls")),
    path("api/v1/reporting/", include("apps.reporting.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/ai/", include("apps.ai_engine.urls")),
]

