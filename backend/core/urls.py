import os

from django.conf import settings
from django.contrib import admin
from django.http import Http404, JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from core.jwt import GrcTokenObtainPairView


def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "error", "db": db_ok}, status=status)


def serve_manual(request, manual_type):
    """Serve il contenuto del manuale Markdown come JSON."""
    filename_map = {
        "utente":  "MANUAL_UTENTE.md",
        "tecnico": "MANUAL_TECNICO.md",
    }
    filename = filename_map.get(manual_type)
    if not filename:
        raise Http404("Manuale non trovato")

    # Cerca il file nella root del progetto (un livello sopra BASE_DIR /app/backend)
    for base in (
        os.path.join(settings.BASE_DIR, "..", ".."),
        os.path.join(settings.BASE_DIR, ".."),
        settings.BASE_DIR,
    ):
        candidate = os.path.normpath(os.path.join(base, filename))
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return JsonResponse({"type": manual_type, "content": f.read()})

    raise Http404("File manuale non trovato")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/manual/<str:manual_type>/", serve_manual, name="manual"),
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
    path("api/v1/schedule/", include("apps.compliance_schedule.urls")),
]

