"""DNS Enricher — lookup nativo via dnspython.

Raccoglie SPF, DMARC, MX, DNSSEC.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan, OsintSettings

logger = logging.getLogger(__name__)


def _txt_records(domain: str) -> list[str]:
    import dns.resolver
    try:
        answers = dns.resolver.resolve(domain, "TXT", raise_on_no_answer=False)
        return [b"".join(r.strings).decode(errors="replace") for r in answers]
    except Exception:
        return []


def _check_spf(txts: list[str]) -> tuple[bool, str]:
    """(present, policy). policy = 'pass'|'softfail'|'fail'|'+all'|'unknown'"""
    for txt in txts:
        if txt.startswith("v=spf1"):
            if "+all" in txt:
                return True, "+all"
            elif "-all" in txt:
                return True, "fail"
            elif "~all" in txt:
                return True, "softfail"
            elif "?all" in txt:
                return True, "neutral"
            return True, "pass"
    return False, ""


def _check_dmarc(domain: str) -> tuple[bool, str]:
    """(present, policy). policy = 'none'|'quarantine'|'reject'"""
    import dns.resolver
    try:
        txts = []
        answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT", raise_on_no_answer=False)
        txts = [b"".join(r.strings).decode(errors="replace") for r in answers]
    except Exception:
        return False, ""

    for txt in txts:
        if "v=DMARC1" in txt:
            if "p=reject" in txt:
                return True, "reject"
            elif "p=quarantine" in txt:
                return True, "quarantine"
            elif "p=none" in txt:
                return True, "none"
            return True, "unknown"
    return False, ""


def _check_mx(domain: str) -> bool:
    import dns.resolver
    try:
        dns.resolver.resolve(domain, "MX", raise_on_no_answer=False)
        return True
    except Exception:
        return False


def _check_dnssec(domain: str) -> bool:
    import dns.resolver
    try:
        dns.resolver.resolve(domain, "RRSIG", raise_on_no_answer=False)
        return True
    except Exception:
        return False


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    domain = entity.domain
    try:
        txts = _txt_records(domain)
        spf_present, spf_policy = _check_spf(txts)
        dmarc_present, dmarc_policy = _check_dmarc(domain)
        mx_present = _check_mx(domain)
        dnssec_enabled = _check_dnssec(domain)

        scan.spf_present = spf_present
        scan.spf_policy = spf_policy
        scan.dmarc_present = dmarc_present
        scan.dmarc_policy = dmarc_policy
        scan.mx_present = mx_present
        scan.dnssec_enabled = dnssec_enabled
        return True
    except Exception as exc:
        logger.warning("DNS enricher failed for %s: %s", domain, exc)
        scan.enricher_errors["dns"] = str(exc)
        return False
