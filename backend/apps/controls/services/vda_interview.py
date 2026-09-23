"""Intervista guidata per la "Implementation description" VDA ISA (TISAX).

Schema "da auditor" (sostituisce la prima versione una-domanda-per-requisito,
che dava poco contesto e faceva ripetere le stesse risposte):
1. i requisiti del controllo (must / should / alta / molto alta protezione) si
   leggono dalla descrizione inglese del framework JSON — per un controllo VH
   anche quelli del controllo base che estende;
2. l'IA li raggruppa in 2-4 TEMI d'intervista nella lingua dell'utente, ognuno
   con cosa vuole capire l'auditor, cosa citare e un esempio a segnaposto
   (dato normativo pubblico, in cache su `Control.translations[lang]`);
3. l'utente risponde per tema; la "verifica con l'auditor" (max 2 giri) valuta
   la copertura di ogni requisito, fa al massimo 3 domande di approfondimento
   sui buchi, elenca le evidenze che l'auditor chiederà e la maturità che le
   risposte sostengono;
4. la bozza in inglese (+ traduzione per la verifica) si scrive dall'intera
   conversazione, per tema, ogni fatto una volta sola. Non viene salvata: l'utente
   la rivede e la salva con `set_implementation_description` (human-in-the-loop,
   regola #9).

Stato su `ControlInstance.implementation_interview`:
    {"lang", "topics": [...snapshot...], "answers": {topic_id: testo},
     "reviews": [{round, coverage, followups, evidence, maturity, summary, at}],
     "followup_answers": {followup_id: testo}, "updated_at"}
L'intervista resta nella lingua in cui è iniziata (i temi sono una fotografia):
riaprendola in un'altra lingua si vedono i temi originali.
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


MAX_REVIEW_ROUNDS = 2
MAX_FOLLOWUPS = 3
MANDATORY_LEVELS = ("must", "high", "very_high")


def _requirements_version(requirements: list[dict]) -> str:
    return hashlib.sha1("|".join(sorted(r["id"] for r in requirements)).encode()).hexdigest()[:10]


def _cached_topics(control, lang: str, version: str) -> list | None:
    cached = (control.translations.get(lang) or {}).get("interview_topics") or {}
    return cached.get("topics") if cached.get("version") == version else None


def _store_topics(control, lang: str, version: str, topics: list) -> None:
    translations = dict(control.translations or {})
    per_lang = dict(translations.get(lang) or {})
    per_lang["interview_topics"] = {"version": version, "topics": topics}
    translations[lang] = per_lang
    control.translations = translations
    control.save(update_fields=["translations", "updated_at"])


def interview_topics(instance, lang: str, user) -> list[dict]:
    """Temi d'intervista per il controllo nella lingua `lang` (cache o IA).

    La cache sta sul controllo dell'istanza (per un VH copre anche i requisiti
    del base) ed è legata all'insieme dei requisiti: se il framework cambia, i
    temi si rigenerano. Solleva AiNotConfigured / LlmUnavailable."""
    from apps.ai_engine.tasks_ai import generate_interview_topics

    requirements = interview_requirements(instance)
    version = _requirements_version(requirements)
    control = instance.control
    topics = _cached_topics(control, lang, version)
    if topics is None:
        from apps.ai_engine.router import LlmUnavailable
        topics = generate_interview_topics(control, requirements, lang, user)
        if not topics:
            raise LlmUnavailable("Risposta IA senza temi d'intervista validi.")
        _store_topics(control, lang, version, topics)
    return topics


def _state(instance) -> dict:
    return dict(instance.implementation_interview or {})


def _followups(state: dict) -> list[dict]:
    return [f for review in state.get("reviews") or [] for f in review.get("followups") or []]


def get_interview(instance, lang: str, user) -> dict:
    """Temi, requisiti, risposte, verifiche dell'auditor e approfondimenti.

    Se l'intervista è già iniziata si usano i temi salvati (e la loro lingua).
    Se l'IA non è disponibile e l'intervista non è iniziata, `topics` è vuoto e
    `ai_error` lo spiega: la UI mostra solo i requisiti originali."""
    from apps.ai_engine.router import AiNotConfigured, LlmUnavailable

    requirements = interview_requirements(instance)
    state = _state(instance)
    ai_error = ""
    topics = state.get("topics") or []
    if topics:
        lang = state.get("lang") or lang
    else:
        try:
            topics = interview_topics(instance, lang, user)
        except AiNotConfigured:
            ai_error = "not_configured"
        except LlmUnavailable:
            ai_error = "unavailable"

    reviews = state.get("reviews") or []
    return {
        "lang": lang,
        "requirements": [
            {"id": r["id"], "level": r["level"], "source": r["source"], "text_en": r["text"]}
            for r in requirements
        ],
        "topics": topics,
        "answers": state.get("answers") or {},
        "reviews": reviews,
        "followups": _followups(state),
        "followup_answers": state.get("followup_answers") or {},
        "rounds_used": len(reviews),
        "max_rounds": MAX_REVIEW_ROUNDS,
        "declared_maturity": instance.calc_maturity_level,
        "updated_at": state.get("updated_at"),
        "ai_error": ai_error,
    }


def _clean_texts(values, valid_ids: set) -> dict:
    """Testi per id noti, ripuliti e limitati (le chiavi sconosciute si scartano)."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValidationError(_("Formato delle risposte non valido."))
    clean = {}
    for key, value in values.items():
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


def save_interview(instance, answers, followup_answers, lang: str, user,
                   reset_reviews: bool = False) -> dict:
    """Salva risposte e approfondimenti (audit: solo conteggi, mai il testo).

    Al primo salvataggio fissa la fotografia dei temi e la lingua.
    `reset_reviews` azzera verifiche e approfondimenti (le risposte restano):
    serve a ricominciare la verifica dopo aver usato i due giri."""
    from core.audit import log_action

    state = _state(instance)
    if not state.get("topics"):
        state["topics"] = interview_topics(instance, lang, user)
        state["lang"] = lang
    if reset_reviews:
        state["reviews"] = []
        state["followup_answers"] = {}
    state["answers"] = _clean_texts(answers, {t["id"] for t in state["topics"]})
    state["followup_answers"] = _clean_texts(
        followup_answers if not reset_reviews else {},
        {f["id"] for f in _followups(state)},
    )
    state["updated_at"] = timezone.now().isoformat()
    instance.implementation_interview = state
    instance.save(update_fields=["implementation_interview", "updated_at"])
    log_action(
        user=user,
        action_code="control.vda_interview_saved",
        level="L3",
        entity=instance,
        payload={
            "answered": len(state["answers"]),
            "followups_answered": len(state["followup_answers"]),
            "reviews_reset": reset_reviews,
            "lang": state["lang"],
        },
    )
    return state


def _conversation(state: dict) -> tuple[list[dict], list[dict]]:
    """(temi con risposta, approfondimenti con risposta) per i prompt IA."""
    answers = state.get("answers") or {}
    fu_answers = state.get("followup_answers") or {}
    topics = [
        {"question": t["question"], "answer": answers.get(t["id"], "")}
        for t in state.get("topics") or []
    ]
    followups = [
        {"question": f["question"], "answer": fu_answers.get(f["id"], "")}
        for f in _followups(state)
    ]
    return topics, followups


def review_interview(instance, answers, followup_answers, lang: str, user) -> dict:
    """Salva e chiede la verifica "da auditor" (giro N di MAX_REVIEW_ROUNDS)."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from apps.ai_engine.tasks_ai import review_vda_interview
    from core.audit import log_action

    state = save_interview(instance, answers, followup_answers, lang, user)
    reviews = state.get("reviews") or []
    if len(reviews) >= MAX_REVIEW_ROUNDS:
        raise ValidationError(
            _("Hai già usato i %(max)s giri di verifica.") % {"max": MAX_REVIEW_ROUNDS}
        )
    if not state["answers"]:
        raise ValidationError(_("Rispondi ad almeno una domanda prima della verifica."))

    round_no = len(reviews) + 1
    requirements = interview_requirements(instance)
    topics, followups = _conversation(state)
    references = _reference_labels(instance)
    result = review_vda_interview(
        instance, requirements, topics, followups, references,
        state["lang"], round_no, MAX_REVIEW_ROUNDS, user,
    )

    valid_ids = {r["id"] for r in requirements}
    coverage = {
        rid: (result["coverage"].get(rid) if result["coverage"].get(rid) in ("covered", "partial", "missing")
              else "missing")
        for rid in (r["id"] for r in requirements)
    }
    review = {
        "round": round_no,
        "at": timezone.now().isoformat(),
        "summary": result["summary"],
        "coverage": coverage,
        "followups": [
            {
                "id": f"f{round_no}_{i + 1}",
                "round": round_no,
                "question": f["question"],
                "req_ids": [x for x in f["req_ids"] if x in valid_ids],
            }
            for i, f in enumerate(result["followups"][:MAX_FOLLOWUPS])
        ],
        "evidence": [
            {"item": e["item"], "linked": e["linked"] if e["linked"] in references else ""}
            for e in result["evidence"][:6]
        ],
        "maturity": result["maturity"],
        "interaction_id": result["interaction_id"],
    }
    state["reviews"] = reviews + [review]
    instance.implementation_interview = state
    instance.save(update_fields=["implementation_interview", "updated_at"])
    log_action(
        user=user,
        action_code="control.vda_interview_reviewed",
        level="L3",
        entity=instance,
        payload={
            "round": round_no,
            "covered": sum(1 for v in coverage.values() if v == "covered"),
            "partial": sum(1 for v in coverage.values() if v == "partial"),
            "missing": sum(1 for v in coverage.values() if v == "missing"),
            "supported_maturity": review["maturity"]["supported_level"],
        },
    )
    return review


def draft_implementation(instance, answers, followup_answers, lang: str, user) -> dict:
    """Salva e chiede all'IA la bozza (EN + lingua utente) dall'intera conversazione.

    I requisiti obbligatori ancora scoperti vengono dall'ultima verifica
    dell'auditor (fatto registrato, non reinterpretato qui); senza verifica è
    l'IA a segnarli con [TO BE COMPLETED]."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from apps.ai_engine.tasks_ai import draft_vda_implementation

    state = save_interview(instance, answers, followup_answers, lang, user)
    if not state["answers"]:
        raise ValidationError(_("Rispondi ad almeno una domanda prima di generare la bozza."))
    requirements = interview_requirements(instance)
    topics, followups = _conversation(state)
    reviews = state.get("reviews") or []
    gaps = None
    if reviews:
        coverage = reviews[-1]["coverage"]
        gaps = [r for r in requirements
                if r["level"] in MANDATORY_LEVELS and coverage.get(r["id"]) == "missing"]
    result = draft_vda_implementation(
        instance, requirements, topics, followups, gaps,
        _reference_labels(instance), state["lang"], user,
    )
    return {
        "draft_en": result["draft_en"],
        "draft_local": result["draft_local"],
        "gaps": [r["id"] for r in gaps] if gaps is not None else [],
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
