import os

from django.conf import settings
from django.contrib import admin
from django.http import Http404, JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.authentication import JWTAuthentication
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


# Whitelist completa tipo+lingua → nome file esatto.
# Nessun input utente viene mai usato per costruire il path.
_MANUAL_FILES = {
    ("utente",  "it"): "MANUAL_UTENTE_it.md",
    ("utente",  "en"): "MANUAL_UTENTE_en.md",
    ("utente",  "fr"): "MANUAL_UTENTE_fr.md",
    ("utente",  "pl"): "MANUAL_UTENTE_pl.md",
    ("utente",  "tr"): "MANUAL_UTENTE_tr.md",
    ("tecnico", "it"): "MANUAL_TECNICO_it.md",
    ("tecnico", "en"): "MANUAL_TECNICO_en.md",
    ("tecnico", "fr"): "MANUAL_TECNICO_fr.md",
    ("tecnico", "pl"): "MANUAL_TECNICO_pl.md",
    ("tecnico", "tr"): "MANUAL_TECNICO_tr.md",
}


def serve_manual(request, manual_type):
    """
    Serve il contenuto del manuale Markdown come JSON.
    Richiede JWT valido. Path completamente whitelist-based — nessun
    input utente nel filename (defense-in-depth contro path traversal).
    """
    # Autenticazione JWT obbligatoria
    try:
        result = JWTAuthentication().authenticate(request)
        if result is None:
            return JsonResponse({"error": "Autenticazione richiesta"}, status=401)
    except Exception:
        return JsonResponse({"error": "Token non valido o scaduto"}, status=401)

    # Lingua dall'header Accept-Language — solo whitelist
    accept_lang = request.headers.get("Accept-Language", "it")
    lang = accept_lang.split(",")[0].split("-")[0].strip().lower()
    if lang not in ("it", "en", "fr", "pl", "tr"):
        lang = "it"

    # Lookup nella whitelist — fallback italiano se la combo non esiste
    fname = _MANUAL_FILES.get((manual_type, lang)) or _MANUAL_FILES.get((manual_type, "it"))
    if not fname:
        raise Http404("Manuale non trovato")

    # Path costruito solo da costanti — nessun input utente
    manual_dir = os.path.realpath(os.path.join(settings.BASE_DIR, "manual"))
    filepath    = os.path.realpath(os.path.join(manual_dir, fname))

    # Verifica difensiva (defense-in-depth): il file è dentro manual_dir
    if not filepath.startswith(manual_dir + os.sep):
        raise Http404("Accesso negato")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return JsonResponse({"type": manual_type, "lang": lang, "content": f.read()})
    except FileNotFoundError:
        raise Http404("File manuale non trovato")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/manual/<str:manual_type>/", serve_manual, name="manual"),
    path("api/v1/manual/<str:manual_type>/", serve_manual, name="manual-v1"),
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

