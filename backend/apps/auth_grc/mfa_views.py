"""
Endpoints MFA per gli utenti del frontend React.
- GET  /api/v1/auth/mfa/status/          → stato MFA attivo/disattivo
- GET  /api/v1/auth/mfa/setup/           → avvia setup: crea device non confermato, restituisce QR
- POST /api/v1/auth/mfa/setup/confirm/   → conferma il device con il primo codice OTP
- DELETE /api/v1/auth/mfa/device/        → disabilita MFA (rimuove tutti i device)
"""
import base64
import binascii
import io
import os

import qrcode
import qrcode.image.svg
from django.apps import apps
from django.contrib.sites.shortcuts import get_current_site
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _get_or_create_pending_device(user):
    """
    Restituisce il device non ancora confermato, oppure ne crea uno nuovo.
    Se esiste già un device confermato, restituisce None (MFA già attivo).
    """
    confirmed = list(devices_for_user(user))
    if confirmed:
        return None  # MFA già attivo

    # Cerca un device pendente (non confermato)
    pending = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if pending:
        return pending

    key = binascii.hexlify(os.urandom(20)).decode()
    return TOTPDevice.objects.create(user=user, name="default", key=key, confirmed=False)


def _otpauth_url(user, device, issuer):
    raw = binascii.unhexlify(device.key)
    b32 = base64.b32encode(raw).decode()
    username = user.get_username()
    return f"otpauth://totp/{issuer}%3A{username}?secret={b32}&issuer={issuer}&digits=6&period=30"


def _qr_png_b64(otpauth_url: str) -> str:
    """Genera un PNG del QR code e lo restituisce come stringa base64."""
    img = qrcode.make(otpauth_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class MfaStatusView(APIView):
    """GET /api/v1/auth/mfa/status/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = bool(list(devices_for_user(request.user)))
        return Response({"enabled": enabled})


class MfaSetupView(APIView):
    """
    GET  → inizia setup, restituisce QR code PNG (base64) + secret key
    POST → conferma device con il primo codice OTP
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device = _get_or_create_pending_device(request.user)
        if device is None:
            return Response(
                {"detail": "MFA già attivo. Disabilita prima di riconfigurare."},
                status=status.HTTP_409_CONFLICT,
            )
        issuer = get_current_site(request).name or "GRC Platform"
        otpauth_url = _otpauth_url(request.user, device, issuer)
        raw = binascii.unhexlify(device.key)
        b32 = base64.b32encode(raw).decode()
        return Response({
            "secret":      b32,
            "otpauth_url": otpauth_url,
            "qr_png":      _qr_png_b64(otpauth_url),  # data:image/png;base64,...
        })

    def post(self, request):
        """Conferma setup: riceve {"code": "123456"}"""
        otp_code = request.data.get("code", "").replace(" ", "")
        if not otp_code:
            return Response({"detail": "Il campo code è obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        # Cerca device pendente
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            return Response(
                {"detail": "Nessun setup in corso. Avvia prima il processo di configurazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify_token(otp_code):
            return Response(
                {"detail": "Codice OTP non valido. Verifica che l'ora del dispositivo sia sincronizzata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save()
        return Response({"detail": "MFA attivato con successo."}, status=status.HTTP_200_OK)


class MfaDisableView(APIView):
    """DELETE /api/v1/auth/mfa/device/ — rimuove tutti i device TOTP dell'utente."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        # Verifica che l'utente fornisca il codice OTP corrente come conferma
        otp_code = request.data.get("code", "").replace(" ", "")
        if not otp_code:
            return Response(
                {"detail": "Inserisci il codice OTP corrente per disabilitare il MFA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        confirmed = list(devices_for_user(request.user))
        if not confirmed:
            return Response({"detail": "MFA non attivo."}, status=status.HTTP_400_BAD_REQUEST)

        verified = any(d.verify_token(otp_code) for d in confirmed)
        if not verified:
            return Response({"detail": "Codice OTP non valido."}, status=status.HTTP_401_UNAUTHORIZED)

        TOTPDevice.objects.filter(user=request.user).delete()

        # Revoca tutti i dispositivi fidati
        from apps.auth_grc.models import TrustedDevice
        for td in TrustedDevice.objects.filter(user=request.user):
            td.revoke()

        return Response({"detail": "MFA disabilitato."}, status=status.HTTP_200_OK)
