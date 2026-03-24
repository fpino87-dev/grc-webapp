"""
Middleware di sicurezza aggiuntivo per GRC Platform.

Aggiunge header HTTP di difesa non coperti da SecurityMiddleware di Django:
- Permissions-Policy: disabilita feature browser non necessarie
- X-Permitted-Cross-Domain-Policies: blocca Adobe Flash/PDF cross-domain
- Cache-Control su risposte API: impedisce caching di dati sensibili

Questi header lavorano in combinazione con le impostazioni Django:
- SECURE_CONTENT_TYPE_NOSNIFF (X-Content-Type-Options: nosniff)
- X_FRAME_OPTIONS: DENY
- SECURE_REFERRER_POLICY: strict-origin-when-cross-origin
"""


class SecurityHeadersMiddleware:
    """
    Aggiunge header di sicurezza a ogni risposta HTTP.
    Deve essere inserito DOPO SecurityMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Disabilita feature browser non necessarie per una webapp aziendale interna
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Blocca policy Adobe Flash/PDF (legacy, defense-in-depth)
        response["X-Permitted-Cross-Domain-Policies"] = "none"

        # Per le API: impedisce caching di dati sensibili nei proxy/browser
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"

        return response
