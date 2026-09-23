"""Intervista guidata per la "Implementation description" VDA ISA (TISAX).

Il flusso:
1. i requisiti del controllo (must / should / alta / molto alta protezione) si
   leggono dalla descrizione inglese del framework JSON — per un controllo VH
   anche quelli del controllo base che estende;
2. l'IA li riformula come domande nella lingua dell'utente (dato normativo
   pubblico, in cache su `Control.translations[lang]["interview_questions"]`);
3. l'utente risponde nella sua lingua; le risposte restano sul controllo
   (`ControlInstance.implementation_interview`) per la rivalutazione successiva;
4. l'IA scrive la bozza in inglese + traduzione nella lingua dell'utente, SOLO
   con i fatti delle risposte. La bozza non viene salvata: l'utente la rivede e
   la salva con `set_implementation_description` (human-in-the-loop, regola #9).
"""
from __future__ import annotations

import hashlib
import re

from django.utils import timezone

ANSWER_MAX = 2000

# Intestazioni di sezione nel testo dei requisiti del framework JSON.
_SECTION_RULES = (
    ("molto alta", "very_high"),
    ("very high", "very_high"),
    ("alta protezione", "high"),
    ("high protection", "high"),
    ("(should)", "should"),
    ("(must)", "must"),
)


def _section_of(line: str) -> str | None:
    low = line.lower()
    for needle, level in _SECTION_RULES:
        if needle in low:
            return level
    return None


def req_id(text: str) -> str:
    """Id stabile del requisito: hash del testo (sopravvive a riordini del JSON)."""
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:10]


def parse_requirements(description: str) -> list[dict]:
    """Estrae i requisiti puntati (`+ ...`) con il loro livello.

    Le righe di continuazione (rientrate, `- ...` o a capo spezzati) vengono
    unite al requisito precedente."""
    out: list[dict] = []
    level = "must"
    current: dict | None = None  # {"level": ..., "parts": [...]}

    def flush():
        if current:
            text = re.sub(r"\s+", " ", " ".join(current["parts"])).strip()
            if text:
                out.append({"id": req_id(text), "level": current["level"], "text": text})

    for raw in (description or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("+"):
            flush()
            current = {"level": level, "parts": [line[1:]]}
            continue
        is_header = not line.startswith((" ", "-", "\t")) and line.endswith(":")
        section = _section_of(line) if is_header else None
        if section:
            flush()
            current = None
            level = section
        elif current is not None:
            current["parts"].append(line)
    flush()
    return out


def _base_control(control):
    """Controllo base esteso da un controllo VH (`ControlMapping(extends)`)."""
    mapping = (
        control.mappings_from.filter(relationship="extends", deleted_at__isnull=True)
        .select_related("target_control")
        .first()
    )
    return mapping.target_control if mapping else None


def interview_requirements(instance) -> list[dict]:
    """Requisiti dell'intervista per l'istanza: base (se VH) + propri, senza doppioni."""
    control = instance.control
    sources = []
    if control.external_id.endswith("-VH"):
        base = _base_control(control)
        if base is not None:
            sources.append(("L2", base))
    sources.append((control.level or "", control))

    seen: set[str] = set()
    out: list[dict] = []
    for source, ctrl in sources:
        for r in parse_requirements((ctrl.translations.get("en") or {}).get("description", "")):
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            out.append({**r, "source": source, "control_id": str(ctrl.pk)})
    return out


def _cached_questions(control, lang: str) -> dict:
    return dict((control.translations.get(lang) or {}).get("interview_questions") or {})


def _store_questions(control, lang: str, questions: dict) -> None:
    translations = dict(control.translations or {})
    per_lang = dict(translations.get(lang) or {})
    merged = {**(per_lang.get("interview_questions") or {}), **questions}
    per_lang["interview_questions"] = merged
    translations[lang] = per_lang
    control.translations = translations
    control.save(update_fields=["translations", "updated_at"])


def get_interview(instance, lang: str, user) -> dict:
    """Requisiti + domande nella lingua `lang` + risposte salvate.

    Le domande mancanti vengono generate dall'IA (una chiamata per controllo)
    e messe in cache. Se l'IA non è disponibile si ritorna comunque l'elenco,
    con `question` vuota: la UI mostra il requisito originale in inglese."""
    from apps.ai_engine.router import AiNotConfigured, LlmUnavailable
    from apps.ai_engine.tasks_ai import generate_interview_questions

    from ..models import Control

    requirements = interview_requirements(instance)
    ai_error = ""
    by_control: dict[str, list[dict]] = {}
    for r in requirements:
        by_control.setdefault(r["control_id"], []).append(r)

    questions: dict[str, str] = {}
    for control_id, reqs in by_control.items():
        control = instance.control if str(instance.control_id) == control_id else Control.objects.get(pk=control_id)
        cached = _cached_questions(control, lang)
        missing = [r for r in reqs if r["id"] not in cached]
        if missing and not ai_error:
            try:
                generated = generate_interview_questions(control, missing, lang, user)
            except AiNotConfigured:
                ai_error = "not_configured"
                generated = {}
            except LlmUnavailable:
                ai_error = "unavailable"
                generated = {}
            if generated:
                _store_questions(control, lang, generated)
                cached.update(generated)
        questions.update({r["id"]: cached.get(r["id"], "") for r in reqs})

    stored = instance.implementation_interview or {}
    answers = stored.get("answers") or {}
    return {
        "lang": lang,
        "requirements": [
            {
                "id": r["id"],
                "level": r["level"],
                "source": r["source"],
                "text_en": r["text"],
                "question": questions.get(r["id"], ""),
            }
            for r in requirements
        ],
        "answers": {r["id"]: answers.get(r["id"], "") for r in requirements},
        "answers_lang": stored.get("lang", ""),
        "answers_updated_at": stored.get("updated_at"),
        "ai_error": ai_error,
    }


def _clean_answers(instance, answers) -> dict:
    """Solo risposte a requisiti del controllo, testo ripulito e limitato."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if not isinstance(answers, dict):
        raise ValidationError(_("Formato delle risposte non valido."))
    valid_ids = {r["id"] for r in interview_requirements(instance)}
    clean = {}
    for key, value in answers.items():
        if key not in valid_ids or not isinstance(value, str):
            continue
        value = value.strip()
        if len(value) > ANSWER_MAX:
            raise ValidationError(
                _("Una risposta supera %(max)s caratteri.") % {"max": ANSWER_MAX}
            )
        if value:
            clean[key] = value
    return clean


def save_interview_answers(instance, answers, lang: str, user) -> dict:
    """Salva le risposte dell'intervista (audit: solo conteggi, mai il testo)."""
    from core.audit import log_action

    clean = _clean_answers(instance, answers)
    instance.implementation_interview = {
        "lang": lang,
        "answers": clean,
        "updated_at": timezone.now().isoformat(),
    }
    instance.save(update_fields=["implementation_interview", "updated_at"])
    log_action(
        user=user,
        action_code="control.vda_interview_saved",
        level="L3",
        entity=instance,
        payload={"answered": len(clean), "lang": lang},
    )
    return clean


def draft_implementation(instance, answers, lang: str, user) -> dict:
    """Salva le risposte e chiede all'IA la bozza (EN + lingua utente).

    `unanswered` è calcolato qui, non dall'IA: i requisiti senza risposta sono
    un fatto, non un'interpretazione. `not_implemented` viene dall'IA
    (risposte che dichiarano che il requisito non è soddisfatto) ed è filtrato
    sugli id reali."""
    from apps.ai_engine.tasks_ai import draft_vda_implementation

    clean = save_interview_answers(instance, answers, lang, user)
    requirements = interview_requirements(instance)
    references = _reference_labels(instance)
    result = draft_vda_implementation(instance, requirements, clean, references, lang, user)

    valid_ids = {r["id"] for r in requirements}
    return {
        "draft_en": result["draft_en"],
        "draft_local": result["draft_local"],
        "unanswered": [r["id"] for r in requirements if r["id"] not in clean],
        "not_implemented": [i for i in result["not_implemented"] if i in valid_ids],
        "interaction_id": result["interaction_id"],
        "provider": result["provider"],
        "model": result["model"],
        "used_fallback": result["used_fallback"],
    }


def _reference_labels(instance) -> list[str]:
    """Titoli di documenti ed evidenze collegati: l'IA può citarli per nome."""
    labels = []
    for d in instance.documents.filter(deleted_at__isnull=True).only("document_code", "title"):
        labels.append(" ".join(p for p in (d.document_code, d.title) if p))
    for ev in instance.evidences.filter(deleted_at__isnull=True).only("title"):
        labels.append(ev.title)
    return labels[:30]
