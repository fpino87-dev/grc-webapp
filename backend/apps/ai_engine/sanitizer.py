import re
import ipaddress
from typing import Tuple

from django.contrib.auth import get_user_model

User = get_user_model()


class Sanitizer:
    """Pseudonimizza dati riconosciuti; non garantisce anonimato del testo libero."""

    # IP: valida solo ottetti 0-255 (evita falsi positivi su numeri generici)
    IP_RE = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    )
    PIVA_RE = re.compile(r"\b\d{11}\b")
    EMAIL_RE = re.compile(r"\b[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
    PHONE_RE = re.compile(r"\b(\+39|0039)?[\s\-]?(\d{2,4})[\s\-]?(\d{6,8})\b")
    PHONE_MOBILE_RE = re.compile(r"\b3\d{2}[\s\-]?\d{6,7}\b")
    # CF: 16 caratteri con struttura fissa, case-insensitive (gestito applicando upper() prima del match)
    CF_RE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")

    IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.I)
    IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*(?:%[\w]+)?", re.I)
    INTERNAL_URL_RE = re.compile(r"https?://[^\s<>]+", re.I)

    @staticmethod
    def _ipv6(match):
        try:
            ipaddress.IPv6Address(match.group().split("%")[0].rstrip("."))
            return "[IP_REMOVED]"
        except ValueError:
            return match.group()

    def sanitize(self, context: dict, plant_ids: list | None = None) -> Tuple[dict, dict]:
        token_map: dict[str, str] = {}
        text = str(context.get("text", ""))
        text, token_map = self._replace_known_entities(text, token_map, plant_ids or [])
        text = self.IPV6_RE.sub(self._ipv6, text)
        text = self.IBAN_RE.sub("[IBAN_REMOVED]", text)
        text = self.INTERNAL_URL_RE.sub("[URL_REMOVED]", text)
        text = self.IP_RE.sub("[IP_REMOVED]", text)
        text = self.PIVA_RE.sub("[PIVA_REMOVED]", text)
        text = self.EMAIL_RE.sub("[EMAIL_REMOVED]", text)
        text = self.PHONE_RE.sub("[PHONE_REMOVED]", text)
        text = self.PHONE_MOBILE_RE.sub("[PHONE_REMOVED]", text)
        # CF: applica su versione uppercase per catturare varianti lowercase
        text_upper = text.upper()
        cf_matches = list(self.CF_RE.finditer(text_upper))
        for m in reversed(cf_matches):
            text = text[: m.start()] + "[CF_REMOVED]" + text[m.end() :]
        return {**context, "text": text}, token_map

    def desanitize(self, text: str, token_map: dict) -> str:
        for token, real_value in token_map.items():
            text = text.replace(token, real_value)
        return text

    def _replace_known_entities(self, text: str, token_map: dict, plant_ids: list) -> Tuple[str, dict]:
        from apps.plants.models import Plant

        plants = Plant.objects.filter(pk__in=plant_ids).select_related("bu").order_by("pk")
        entities = []
        for i, plant in enumerate(plants):
            entities.extend([(plant.name, f"[PLANT_{chr(65 + i)}]"),
                             (plant.code, f"[PLANT_{chr(65 + i)}_CODE]")])
            if plant.bu_id:
                entities.append((plant.bu.name, f"[BU_{i}]"))
        # Match known full names and infrastructure identifiers, not arbitrary
        # capitalized words. This is pseudonymization, never guaranteed anonymity.
        from apps.assets.models import Asset
        from apps.suppliers.models import Supplier
        for i, name in enumerate(Asset.objects.filter(plant_id__in=plant_ids).values_list("name", flat=True)):
            entities.append((name, f"[ASSET_{i}]"))
        for i, name in enumerate(Supplier.objects.filter(plants__in=plant_ids).distinct().values_list("name", flat=True)):
            entities.append((name, f"[SUPPLIER_{i}]"))
        for i, (first, last) in enumerate(User.objects.exclude(first_name="").exclude(last_name="").values_list("first_name", "last_name")):
            entities.append((f"{first} {last}", f"[PERSON_{i}]"))
        for value, token in sorted(entities, key=lambda item: len(item[0] or ""), reverse=True):
            if value and len(value) >= 3:
                pattern = re.compile(r"(?<!\w)" + re.escape(value) + r"(?!\w)", re.I)
                if pattern.search(text):
                    text = pattern.sub(token, text)
                    token_map[token] = value
        return text, token_map
