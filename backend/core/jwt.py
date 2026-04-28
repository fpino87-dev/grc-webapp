from django.core import signing
from django_otp import devices_for_user
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

_MFA_SALT = "grc-mfa-token"
_MFA_TTL = 300  # 5 minuti


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


def _fingerprint_source(request) -> str:
    """
    Costruisce la stringa input per `compute_device_fingerprint` (newfix S8).
    Combina User-Agent e Accept-Language (header presenti su qualunque browser
    reale). NON include l'IP: cambia troppo spesso (mobile, VPN aziendali) e
    aprirebbe falsi negativi su utenti legittimi.

    Formato `ua\x01lang` per evitare collisioni su separatori naturali.
    """
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
    lang = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "")[:200]
    if not ua and not lang:
        return ""
    return f"{ua}\x01{lang}"


# Gerarchia ruoli (newfix R2): determina il "ruolo dominante" da esporre come
# `role` legacy quando l'utente ha piu' UserPlantAccess. L'ordine va dal piu'
# alto al piu' basso; chi compare prima nella lista vince.
_ROLE_HIERARCHY = (
    "super_admin",
    "compliance_officer",
    "internal_auditor",
    "external_auditor",
    "risk_manager",
    "plant_manager",
    "control_owner",
)


def _highest_role(roles):
    for r in _ROLE_HIERARCHY:
        if r in roles:
            return r
    return next(iter(roles), "user")


class GrcTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["is_superuser"] = user.is_superuser

        # newfix R2 — espone TUTTI i ruoli e la mappa role-per-plant.
        # Il claim `role` resta per retro-compatibilita' UI: e' il "ruolo piu'
        # alto" secondo _ROLE_HIERARCHY tra tutti i UserPlantAccess attivi.
        from apps.auth_grc.models import UserPlantAccess

        access_qs = UserPlantAccess.objects.filter(
            user=user, deleted_at__isnull=True,
        ).prefetch_related("scope_plants")

        roles = sorted({a.role for a in access_qs})
        roles_by_plant: dict[str, list[str]] = {}
        for access in access_qs:
            if access.scope_type == "org":
                roles_by_plant.setdefault("__org__", []).append(access.role)
            elif access.scope_type == "bu" and access.scope_bu_id:
                roles_by_plant.setdefault(f"bu:{access.scope_bu_id}", []).append(access.role)
            elif access.scope_type in ("plant_list", "single_plant"):
                for plant in access.scope_plants.all():
                    roles_by_plant.setdefault(str(plant.pk), []).append(access.role)

        if roles:
            token["roles"] = roles
            token["role"] = _highest_role(roles)
        elif user.is_superuser:
            token["roles"] = ["super_admin"]
            token["role"] = "super_admin"
        else:
            token["roles"] = []
            token["role"] = "user"
        token["roles_by_plant"] = roles_by_plant
        return token


def _issue_jwt(user):
    """Restituisce il dict {access, refresh} per l'utente dato."""
    refresh = GrcTokenObtainPairSerializer.get_token(user)
    return {
        "refresh": str(refresh),
        "access":  str(refresh.access_token),
    }


class GrcTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/token/
    - Credenziali valide, nessun device TOTP → JWT immediato (HTTP 200)
    - Credenziali valide, device TOTP presente → mfa_required (HTTP 202)
    """
    serializer_class = GrcTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"detail": "Credenziali non valide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.user
        if list(devices_for_user(user)):
            # Controlla se il dispositivo è già fidato (bypass MFA per 30 giorni)
            device_token = request.data.get("device_token", "")
            if device_token:
                from apps.auth_grc.models import TrustedDevice
                # newfix S8: verify richiede anche match del fingerprint del
                # browser (UA + Accept-Language + SECRET_KEY pepper). Token
                # legacy senza fingerprint_hash sono rifiutati.
                if TrustedDevice.verify(
                    user, device_token, fingerprint_source=_fingerprint_source(request),
                ):
                    return Response(_issue_jwt(user), status=status.HTTP_200_OK)

            # Utente ha MFA attivo: emetti un token temporaneo, NON il JWT
            mfa_token = signing.dumps(
                {"uid": str(user.pk)},
                salt=_MFA_SALT,
            )
            return Response(
                {"mfa_required": True, "mfa_token": mfa_token},
                status=status.HTTP_202_ACCEPTED,
            )

        # Nessun device — emetti JWT direttamente
        return Response(_issue_jwt(user), status=status.HTTP_200_OK)


class MfaVerifyView(APIView):
    """
    POST /api/token/mfa/
    Body: {"mfa_token": "...", "otp_code": "123456"}
    Verifica il codice TOTP e, se corretto, restituisce il JWT.
    """
    throttle_classes = [LoginRateThrottle]
    permission_classes = []  # unauthenticated

    def post(self, request):
        mfa_token = request.data.get("mfa_token", "")
        otp_code  = request.data.get("otp_code", "").replace(" ", "")

        if not mfa_token or not otp_code:
            return Response(
                {"detail": "mfa_token e otp_code sono obbligatori."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Valida e decodifica il token temporaneo (scade in 5 min)
        try:
            data = signing.loads(mfa_token, salt=_MFA_SALT, max_age=_MFA_TTL)
        except signing.SignatureExpired:
            return Response(
                {"detail": "Sessione scaduta. Effettua di nuovo il login."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Token non valido."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(pk=data["uid"])
        except (User.DoesNotExist, KeyError):
            return Response({"detail": "Utente non trovato."}, status=status.HTTP_401_UNAUTHORIZED)

        # Verifica il codice OTP su tutti i device confermati dell'utente
        verified = False
        for device in devices_for_user(user):
            if device.verify_token(otp_code):
                verified = True
                break

        if not verified:
            return Response(
                {"detail": "Codice OTP non valido o scaduto."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response_data = _issue_jwt(user)

        # Se il client chiede di fidarsi di questo dispositivo, emetti un token da 30 giorni
        if request.data.get("trust_device"):
            device_name = request.META.get("HTTP_USER_AGENT", "")[:200]
            from apps.auth_grc.models import TrustedDevice
            # newfix S8 — il fingerprint viene legato all'emissione e
            # richiesto identico nelle verify successive.
            _, raw_token = TrustedDevice.create_for_user(
                user, device_name,
                fingerprint_source=_fingerprint_source(request),
            )
            response_data["device_token"] = raw_token

        return Response(response_data, status=status.HTTP_200_OK)
