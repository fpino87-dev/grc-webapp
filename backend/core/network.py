"""
Identificazione dell'IP client dietro reverse proxy (newfix 2026-06-09 #5).

`REMOTE_ADDR` dietro NPM/Nginx è l'IP del proxy, non del client; l'header
X-Forwarded-For è invece spoofabile dal client (può preporre valori arbitrari).
Il proxy fidato APPENDE l'IP reale del client in coda all'XFF, quindi con N
proxy fidati l'IP affidabile è l'N-esimo da destra — stessa semantica di
`NUM_PROXIES` usata dal throttling DRF (`BaseThrottle.get_ident`), così
throttle e audit log identificano il client allo stesso modo.

Uso: payload audit di login/logout (core/jwt.py) e qualunque punto che debba
loggare l'IP del client. Mai usare REMOTE_ADDR o XFF grezzi direttamente.
"""
from django.conf import settings


def get_client_ip(request) -> str:
    """
    Ritorna l'IP del client secondo `REST_FRAMEWORK["NUM_PROXIES"]`:
    - num_proxies è None → XFF intero se presente, altrimenti REMOTE_ADDR
      (comportamento legacy DRF, sconsigliato);
    - num_proxies == 0 → sempre REMOTE_ADDR (nessun proxy fidato);
    - num_proxies >= 1 → N-esimo indirizzo da destra dell'XFF (gli hop
      aggiunti dai proxy fidati), REMOTE_ADDR se l'header manca.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    remote_addr = request.META.get("REMOTE_ADDR") or ""
    num_proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES")

    if num_proxies is not None:
        if num_proxies == 0 or not xff:
            return remote_addr
        addrs = xff.split(",")
        return addrs[-min(num_proxies, len(addrs))].strip()

    return "".join(xff.split()) if xff else remote_addr
