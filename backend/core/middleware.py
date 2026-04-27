"""
Middleware di sicurezza aggiuntivo per GRC Platform.

Aggiunge header HTTP di difesa non coperti da SecurityMiddleware di Django:
- Permissions-Policy: disabilita feature browser non necessarie
- X-Permitted-Cross-Domain-Policies: blocca Adobe Flash/PDF cross-domain
- Content-Security-Policy: limita origini per script/style/connect/form
- Cache-Control su risposte API: impedisce caching di dati sensibili

Questi header lavorano in combinazione con le impostazioni Django:
- SECURE_CONTENT_TYPE_NOSNIFF (X-Content-Type-Options: nosniff)
- X_FRAME_OPTIONS: DENY
- SECURE_REFERRER_POLICY: strict-origin-when-cross-origin
"""

def _build_csp() -> str:
    """
    CSP per le pagine HTML servite dal backend Django (admin, wizard 2FA).
    La SPA React è servita da nginx con CSP separata in INFRASTRUCTURE.md.

    - 'unsafe-inline' è richiesto da Django admin (widget autocomplete, calendario);
      per il futuro valutare nonces se si dismette l'admin.
    - connect-src include Sentry se SENTRY_DSN configurato.
    """
    import os

    connect_src = ["'self'"]
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    # Estraiamo l'host Sentry da DSN (formato https://key@host/project) per la connect-src.
    if sentry_dsn:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(sentry_dsn)
            if parsed.hostname:
                connect_src.append(f"https://{parsed.hostname}")
        except Exception:
            pass

    directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        f"connect-src {' '.join(connect_src)}",
        "font-src 'self' data:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
    return "; ".join(directives)


class SecurityHeadersMiddleware:
    """
    Aggiunge header di sicurezza a ogni risposta HTTP.
    Deve essere inserito DOPO SecurityMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._csp = _build_csp()

    def __call__(self, request):
        response = self.get_response(request)

        # Disabilita feature browser non necessarie per una webapp aziendale interna
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Blocca policy Adobe Flash/PDF (legacy, defense-in-depth)
        response["X-Permitted-Cross-Domain-Policies"] = "none"

        # Content-Security-Policy: applichiamo a tutte le risposte. Sui JSON il
        # browser ignora la policy; sulle pagine HTML (admin, wizard 2FA) limita
        # l'esecuzione di codice esterno e la submit di form fuori origine.
        response.setdefault("Content-Security-Policy", self._csp)

        # Per le API: impedisce caching di dati sensibili nei proxy/browser
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"

        return response
