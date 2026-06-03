"""Certificate Transparency monitoring (crt.sh).

Riusa la risposta crt.sh già scaricata dall'enricher SSL (per i sottodomini): non
fa una seconda chiamata di rete. Analizza i certificati **emessi di recente** per
il dominio e, se è configurata un'allowlist di CA attese
(`OsintSettings.ct_expected_issuers`), segnala gli issuer fuori allowlist come
**potenziale mis-issuance** (certificato emesso da una CA che l'organizzazione non
usa → possibile shadow IT, dominio compromesso o infrastruttura di phishing).

Tutto in-memory sulle entry già caricate: nessun side-effect di rete qui.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as tz
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)

# Cap difensivo sul numero di certificati recenti memorizzati nello scan.
CT_MAX_RECENT = 50
# Cap sui nomi (SAN) salvati per certificato.
CT_MAX_NAMES = 10


def _parse_dt(value: str | None) -> datetime | None:
    """Parsa un timestamp crt.sh ('2024-01-15T12:34:56[.ffffff]', talvolta con 'Z').

    Ritorna un datetime aware (UTC) o None se non parsabile. crt.sh espone
    not_before/entry_timestamp senza timezone esplicito: si assume UTC."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip().replace("Z", "")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        # Fallback: tronca eventuali microsecondi malformati
        try:
            dt = datetime.fromisoformat(raw.split(".")[0])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    return dt


def _names_from_entry(name_value: str | None, domain: str) -> list[str]:
    """Estrae i nomi (SAN) di un'entry crt.sh pertinenti al dominio, deduplicati."""
    out: list[str] = []
    seen: set[str] = set()
    for name in (name_value or "").split("\n"):
        name = name.strip().lower()
        if not name or name in seen:
            continue
        bare = name[2:] if name.startswith("*.") else name
        if bare == domain or bare.endswith(f".{domain}"):
            seen.add(name)
            out.append(name)
    return out


def analyze_ct(
    entity: "OsintEntity",
    scan: "OsintScan",
    entries: list[dict],
    settings: "OsintSettings",
) -> None:
    """Popola `scan.ct_recent_certs` e `scan.ct_unexpected_issuers`.

    No-op se il monitoring CT è disabilitato. Gli issuer "inattesi" vengono
    valorizzati **solo** quando `ct_expected_issuers` è non vuota: senza allowlist
    si offre solo visibilità (nessun falso positivo, nessun alert)."""
    if not getattr(settings, "ct_monitoring_enabled", True):
        return

    lookback = settings.ct_lookback_days or 30
    cutoff = datetime.now(tz=tz.utc) - timedelta(days=lookback)
    expected = [e.strip().lower() for e in (settings.ct_expected_issuers or []) if e and e.strip()]
    domain = entity.domain

    recent: list[dict] = []
    unexpected: set[str] = set()

    for entry in entries:
        issued = _parse_dt(entry.get("not_before")) or _parse_dt(entry.get("entry_timestamp"))
        if issued is None or issued < cutoff:
            continue
        issuer = (entry.get("issuer_name") or "").strip()
        names = _names_from_entry(entry.get("name_value"), domain)
        # Considera solo i certificati con almeno un nome pertinente al dominio:
        # un'entry crt.sh i cui SAN non riguardano il dominio non è un certificato
        # "del dominio" e non deve né comparire tra i recenti né — soprattutto —
        # generare un issuer inatteso (alert CRITICAL spurio).
        if not names:
            continue
        recent.append({
            "id": entry.get("id"),
            "issuer": issuer[:255],
            "names": names[:CT_MAX_NAMES],
            "not_before": (entry.get("not_before") or "")[:32],
            "entry": (entry.get("entry_timestamp") or "")[:32],
        })
        if expected and issuer and not any(exp in issuer.lower() for exp in expected):
            unexpected.add(issuer[:255])

    # Più recenti prima (per il rendering); cap difensivo.
    recent.sort(key=lambda c: c.get("not_before") or "", reverse=True)
    scan.ct_recent_certs = recent[:CT_MAX_RECENT]
    scan.ct_unexpected_issuers = sorted(unexpected)

    if unexpected:
        logger.info(
            "CT monitoring: %d issuer inattesi per %s su %d certificati recenti",
            len(unexpected), domain, len(recent),
        )
