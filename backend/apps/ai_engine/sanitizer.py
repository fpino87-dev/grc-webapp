import re
from typing import Tuple

from django.contrib.auth import get_user_model

User = get_user_model()


class Sanitizer:
    """Anonimizza dati sensibili prima di inviarli al cloud LLM."""

    IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    PIVA_RE = re.compile(r"\b\d{11}\b")
    EMAIL_RE = re.compile(r"\b[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
    PHONE_RE = re.compile(r"\b(\+39|0039)?[\s\-]?(\d{2,4})[\s\-]?(\d{6,8})\b")
    PHONE_MOBILE_RE = re.compile(r"\b3\d{2}[\s\-]?\d{6,7}\b")
    CF_RE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", re.IGNORECASE)

    def sanitize(self, context: dict, plant_ids: list | None = None) -> Tuple[dict, dict]:
        token_map: dict[str, str] = {}
        text = str(context.get("text", ""))
        text, token_map = self._replace_known_entities(text, token_map, plant_ids or [])
        text = self.IP_RE.sub("[IP_REMOVED]", text)
        text = self.PIVA_RE.sub("[REMOVED]", text)
        text = self.EMAIL_RE.sub("[EMAIL_REMOVED]", text)
        text = self.PHONE_RE.sub("[PHONE_REMOVED]", text)
        text = self.PHONE_MOBILE_RE.sub("[PHONE_REMOVED]", text)
        text = self.CF_RE.sub("[CF_REMOVED]", text)
        return {**context, "text": text}, token_map

    def desanitize(self, text: str, token_map: dict) -> str:
        for token, real_value in token_map.items():
            text = text.replace(token, real_value)
        return text

    def _replace_known_entities(self, text: str, token_map: dict, plant_ids: list) -> Tuple[str, dict]:
        from apps.plants.models import Plant

        plants = Plant.objects.filter(pk__in=plant_ids)
        for i, plant in enumerate(plants):
            token = f"[PLANT_{chr(65 + i)}]"
            for val in [plant.name, plant.code]:
                if val and val in text:
                    text = text.replace(val, token)
                    token_map[token] = val
        return text, token_map

