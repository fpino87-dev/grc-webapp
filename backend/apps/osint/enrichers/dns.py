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
    """Parser SPF robusto.

    Ritorna (present, policy). policy può essere:
    - "fail" / "softfail" / "neutral" / "+all" / "pass" (record valido)
    - "permerror_multiple" se esistono più record v=spf1 (RFC 7208 §3.2 → permerror)
    - "permerror_lookup" se i lookup DNS implicit (include/redirect/a/mx/exists/ptr) eccedono 10
    - "redirect" se il record si limita a `redirect=...` senza policy esplicita
    - "" se non presente
    """
    spf_records = [t for t in txts if t.lower().startswith("v=spf1")]
    if not spf_records:
        return False, ""
    if len(spf_records) > 1:
        return True, "permerror_multiple"

    txt = spf_records[0]
    tokens = txt.split()
    # Conta i meccanismi che richiedono lookup DNS (RFC 7208 §4.6.4): include, a, mx,
    # ptr, exists, redirect modifier. Ognuno conta 1.
    lookup_terms = ("include:", "a", "a:", "mx", "mx:", "ptr", "ptr:", "exists:", "redirect=")
    lookup_count = 0
    has_redirect = False
    for tk in tokens[1:]:
        bare = tk.lstrip("+-~?").lower()
        for term in lookup_terms:
            if bare == term.rstrip(":=") or bare.startswith(term):
                lookup_count += 1
                if term == "redirect=":
                    has_redirect = True
                break
    if lookup_count > 10:
        return True, "permerror_lookup"

    low = txt.lower()
    if "+all" in low:
        return True, "+all"
    if "-all" in low:
        return True, "fail"
    if "~all" in low:
        return True, "softfail"
    if "?all" in low:
        return True, "neutral"
    if has_redirect:
        return True, "redirect"
    return True, "pass"


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
    """DNSSEC enabled se il dominio espone DNSKEY *e* il parent ha un DS record.

    Solo RRSIG sull'apex non è affidabile: alcuni resolver autoritativi non lo
    ritornano in `dnspython` con `raise_on_no_answer=False`. La presenza di
    DNSKEY (sul dominio) + DS (sul parent registry) è la firma canonica della
    catena di fiducia DNSSEC attiva.
    """
    import dns.resolver
    import dns.rdatatype

    # 1) DNSKEY sul dominio
    try:
        ans = dns.resolver.resolve(domain, "DNSKEY", raise_on_no_answer=False)
        if not list(ans):
            return False
    except Exception:
        return False

    # 2) DS record nel parent zone (cioè interrogando il dominio stesso ritorna il DS proprio)
    try:
        ans = dns.resolver.resolve(domain, "DS", raise_on_no_answer=False)
        ds_rrs = list(ans)
        return len(ds_rrs) > 0
    except Exception:
        # Per alcune TLD la query DS sul name può non risolvere via il resolver
        # ricorsivo: se DNSKEY è presente accettiamo DNSSEC come probabile.
        return True


def run(entity: "OsintEntity", scan: "OsintScan", settings: "OsintSettings") -> bool:
    from apps.osint.validators import assert_public_or_log

    domain = entity.domain
    if not assert_public_or_log(domain, "dns"):
        scan.enricher_errors["dns"] = "non_public_target"
        return False
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
