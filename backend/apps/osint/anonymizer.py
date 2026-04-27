"""AnonymizationService OSINT — Step 7.

Sostituisce dati identificativi con placeholder sequenziali prima di
inviare il payload a Claude API. La mapping table vive solo in RAM
per la durata della singola richiesta — mai persistita.

Campi DA anonimizzare:
  domain      → [DOM_001], [DOM_002], ...
  display_name (fornitori) → [SUP_001], ...
  display_name (siti)      → [SITE_001], ...
  display_name (asset)     → [ASSET_001], ...
  ip_address   → [IP_001], ...

Campi CHE RESTANO INTATTI: score_*, ssl_*, spf_*, dmarc_*, vt_*, abuse_*,
  otx_pulses, gsb_status, in_blacklist, hibp_*, is_nis2_critical,
  scan_date, delta, asset_type (generico).
"""
from __future__ import annotations

import re
from typing import Any


class AnonymizationService:
    """Crea placeholder sequenziali e gestisce anonymize/deanonymize.

    Uso tipico:
        svc = AnonymizationService()
        anon_payload = svc.anonymize(payload)
        response_text = call_ai(anon_payload)
        final_text = svc.deanonymize(response_text)
    """

    PLACEHOLDER_RE = re.compile(r"\[(DOM|SUP|SITE|ASSET|IP)_\d{3,}\]")

    def __init__(self):
        self._counters: dict[str, int] = {}
        # mapping: real_value → placeholder (for serialization)
        self._to_ph: dict[str, str] = {}
        # reverse: placeholder → real_value (for deanonymize)
        self._from_ph: dict[str, str] = {}

    def _placeholder(self, prefix: str, value: str) -> str:
        if value in self._to_ph:
            return self._to_ph[value]
        count = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = count
        ph = f"[{prefix}_{count:03d}]"
        self._to_ph[value] = ph
        self._from_ph[ph] = value
        return ph

    def anonymize_domain(self, domain: str) -> str:
        return self._placeholder("DOM", domain) if domain else domain

    def anonymize_display_name(self, name: str, entity_type: str) -> str:
        prefix_map = {"my_domain": "SITE", "supplier": "SUP", "asset": "ASSET"}
        prefix = prefix_map.get(entity_type, "SUP")
        return self._placeholder(prefix, name) if name else name

    def anonymize_ip(self, ip: str) -> str:
        return self._placeholder("IP", ip) if ip else ip

    def anonymize(self, payload: Any) -> Any:
        """Ricorsivamente anonimizza stringhe nel payload (dict, list, str)."""
        if isinstance(payload, dict):
            return {k: self._anon_value(k, v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self.anonymize(item) for item in payload]
        return payload

    def _anon_value(self, key: str, value: Any) -> Any:
        """Anonimizza il valore in base alla chiave."""
        if isinstance(value, (dict, list)):
            return self.anonymize(value)
        if not isinstance(value, str) or not value:
            return value
        if key == "domain":
            return self.anonymize_domain(value)
        if key == "display_name":
            # Senza entity_type nel contesto, usa SUP come fallback
            return self._placeholder("SUP", value)
        if key in ("ip_address", "ip"):
            return self.anonymize_ip(value)
        return value

    def anonymize_entity_dict(self, entity_data: dict) -> dict:
        """Anonimizza un dict che rappresenta un'OsintEntity con il tipo corretto."""
        result = dict(entity_data)
        entity_type = entity_data.get("entity_type", "supplier")
        if "domain" in result and result["domain"]:
            result["domain"] = self.anonymize_domain(result["domain"])
        if "display_name" in result and result["display_name"]:
            result["display_name"] = self.anonymize_display_name(
                result["display_name"], entity_type
            )
        return result

    def deanonymize(self, text: str) -> str:
        """Sostituisce tutti i placeholder nella risposta AI con i valori reali."""
        if not text:
            return text

        def replace(m: re.Match) -> str:
            ph = m.group(0)
            return self._from_ph.get(ph, ph)

        return self.PLACEHOLDER_RE.sub(replace, text)


OSINT_SYSTEM_PROMPT = """Sei un esperto di cybersecurity e GRC (Governance, Risk & Compliance).
Stai analizzando dati di monitoraggio OSINT per un'organizzazione.

IMPORTANTE: I dati contengono placeholder anonimizzati nel formato
[DOM_001], [SUP_001], [IP_001], [ASSET_001], [SITE_001] ecc.
Usa SEMPRE questi placeholder nelle tue risposte — non tentare
di inferire, indovinare o sostituire i nomi reali.
Analizza esclusivamente i dati tecnici forniti.

Il tuo obiettivo è produrre analisi chiare, prioritizzate e
actionable — non elenchi di dati tecnici grezzi.
Scrivi per un pubblico misto: CISO, responsabili IT e board.
Lingua: italiano, salvo diversa indicazione nei dati."""
