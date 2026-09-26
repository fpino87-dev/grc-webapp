"""Sintesi executive del riesame con bozza generata dal motore IA (M20).

Regole (CLAUDE.md #9, AI Act art. 50):
- al modello arrivano solo dati aggregati, titoli e testi del verbale; i nomi
  delle persone vengono pseudonimizzati qui e il testo passa comunque dal
  `Sanitizer` del router (email, telefoni, CF, nomi dei siti);
- la bozza non entra mai nel verbale da sola: resta in `executive_summary_draft`
  finché un utente non la accetta (anche modificata);
- i metadati registrano se il testo è assistito dall'IA, con quale modello e
  chi lo ha validato, così la relazione può dichiararlo.
"""
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..agenda import ISO_AGENDA_CLAUSE, ISO_AGENDA_TITLES
from ..models import ManagementReview

LANGUAGE_NAMES = {"it": "italiano", "en": "English", "fr": "français", "pl": "polski", "tr": "Türkçe"}

SYSTEM_PROMPT = (
    "Sei un consulente esperto di sistemi di gestione della sicurezza delle informazioni. "
    "Redigi la sintesi executive del verbale di un riesame di direzione per il vertice "
    "aziendale. Il riesame copre tutti i sistemi di gestione adottati dall'azienda: non "
    "intestarlo a una singola norma e non citare numeri di clausola. Usa esclusivamente i "
    "dati forniti: non inventare numeri, nomi, date o decisioni. I segnaposto tra parentesi "
    "quadre (es. [PERSONA_1], [PLANT_A]) vanno riportati identici; le altre annotazioni fra "
    "parentesi quadre presenti nei dati sono etichette di servizio e non vanno ricopiate nel "
    "testo."
)

DECISION_LABELS = {
    "miglioramento": "miglioramento",
    "modifica_sgsi": "modifica al SGSI",
    "risorse": "risorse",
    "obiettivo": "obiettivo di sicurezza",
    "altro": "altro",
}


def _risk_line(r: dict, owner_label: str) -> str:
    """Riga di sintesi dei rischi per i testi di servizio (sintesi, bozze IA).
    Con gli snapshot allineati al Reporting riporta i rischi oltre la soglia di
    accettabilità approvata; con quelli precedenti la fascia "critici"."""
    tail = (
        f"medi {r.get('giallo', 0)}, bassi {r.get('verde', 0)}, accettati formalmente "
        f"{r.get('accettati_formalmente', 0)}, {owner_label} {r.get('senza_owner', 0)}"
    )
    if "oltre_soglia" in r:
        soglia = (r.get("soglia") or {}).get("max_acceptable_score", 14)
        return (
            f"- Rischi: oltre la soglia di accettabilità (residuo > {soglia}) {r.get('oltre_soglia', 0)} "
            f"(senza piano {r.get('senza_piano', 0)}), alti {r.get('rosso', 0)}, " + tail
        )
    return f"- Rischi: critici {r.get('rosso', 0)} (senza piano {r.get('senza_piano', 0)}), " + tail

def _ensure_editable(review: ManagementReview) -> None:
    if review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è approvato: la sintesi non è più modificabile."))


class _PersonPseudonymizer:
    """Sostituisce i nomi completi degli utenti con [PERSONA_n] e li ripristina."""

    def __init__(self):
        User = get_user_model()
        names = set()
        for first, last in User.objects.values_list("first_name", "last_name"):
            for full in (f"{first} {last}", f"{last} {first}"):
                full = " ".join(full.split())
                if len(full) >= 5 and " " in full:
                    names.add(full)
        # I nomi più lunghi per primi, così "Anna Maria Rossi" non viene spezzato.
        self._names = sorted(names, key=len, reverse=True)
        self._tokens: dict[str, str] = {}

    def apply(self, text: str) -> str:
        for name in self._names:
            pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
            if pattern.search(text):
                token = self._tokens.setdefault(name.lower(), f"[PERSONA_{len(self._tokens) + 1}]")
                text = pattern.sub(token, text)
        return text

    def restore(self, text: str) -> str:
        by_token = {token: name for name, token in self._tokens.items()}
        originals = {n.lower(): n for n in self._names}
        for token, lower in by_token.items():
            text = text.replace(token, originals.get(lower, lower))
        return text


def _fmt_list(items, fmt, limit=5) -> str:
    return "; ".join(fmt(i) for i in (items or [])[:limit])


def build_summary_prompt(review: ManagementReview, lang: str) -> str:
    snap = review.snapshot_data or {}
    lines = [
        f"Riesame: {review.title}",
        f"Data riunione: {review.review_date.isoformat() if review.review_date else '—'}",
        f"Perimetro: {'sito ' + review.plant.name if review.plant_id else 'intera organizzazione'}",
        f"Dati congelati il: {(snap.get('generated_at') or '')[:10]}",
        "",
        "DATI",
    ]

    fws = snap.get("frameworks") or {}
    if fws:
        lines.append("- Compliance per framework: " + "; ".join(
            f"{code} {fw.get('pct_compliant', 0)}% compliant ({fw.get('by_status', {}).get('compliant', 0)}/"
            f"{fw.get('total', 0)}), gap {fw.get('by_status', {}).get('gap', 0)}"
            for code, fw in fws.items()
        ))
    d = snap.get("documenti") or {}
    if d:
        lines.append(
            f"- Documenti: approvati {d.get('approvati', 0)}, scaduti {d.get('scaduti', 0)}, "
            f"in scadenza a 90 giorni {d.get('in_scadenza', 0)}, approvati nel periodo "
            f"{d.get('approvati_periodo', 0)}; evidenze scadute {d.get('evidenze_scadute', 0)}"
        )
    r = snap.get("rischi") or {}
    if r:
        lines.append(_risk_line(r, owner_label="senza owner"))
        top = _fmt_list(r.get("top_critici"), lambda x: f"{x.get('name')} (residuo {x.get('score')})")
        if top:
            label = "Rischi oltre soglia principali" if "oltre_soglia" in r else "Rischi critici principali"
            lines.append(f"  {label}: {top}")
    i = snap.get("incidenti") or {}
    if i:
        lines.append(
            f"- Incidenti ultimi 12 mesi: {i.get('totale_12m', 0)}, notificati NIS2 "
            f"{i.get('nis2_notificati', 0)}, ancora aperti {i.get('aperti', 0)}, chiusi senza RCA "
            f"{i.get('senza_rca', 0)}"
        )
    p = snap.get("pdca") or {}
    t = snap.get("task") or {}
    if p or t:
        lines.append(
            f"- Miglioramento: cicli PDCA aperti {p.get('aperti', 0)}, fermi in PLAN da oltre 90 giorni "
            f"{p.get('bloccati_plan_90gg', 0)}, chiusi nei 12 mesi {p.get('chiusi_12m', 0)}; task scaduti "
            f"{t.get('scaduti', 0)}"
        )
    b = snap.get("bcp") or {}
    if b.get("processi_critici_senza_bcp"):
        lines.append(f"- Continuità: processi critici senza piano BCP {b['processi_critici_senza_bcp']}")
    k = snap.get("kpi") or {}
    if k:
        counts = k.get("status_counts") or {}
        lines.append(
            f"- KPI: {k.get('totale', 0)} monitorati, critici {counts.get('critical', 0)}, "
            f"in attenzione {counts.get('warning', 0)}"
        )
        att = _fmt_list(k.get("elenco_attenzione"), lambda x: f"{x.get('name')} = {x.get('value')}{x.get('unit') or ''}")
        if att:
            lines.append(f"  KPI fuori soglia: {att}")
    a = snap.get("audit") or {}
    if a:
        lines.append(
            f"- Audit: {a.get('audit_12m', 0)} negli ultimi 12 mesi; non conformità aperte maggiori "
            f"{a.get('nc_aperte_maggiori', 0)}, minori {a.get('nc_aperte_minori', 0)}; finding scaduti "
            f"{a.get('finding_scaduti', 0)}; opportunità di miglioramento aperte {a.get('opportunita_aperte', 0)}"
        )
    prev = snap.get("azioni_precedenti") or {}
    if prev.get("riesame_precedente"):
        lines.append(
            f"- Azioni dei riesami precedenti: {prev.get('totale', 0)} considerate, chiuse {prev.get('chiuse', 0)}, "
            f"aperte {prev.get('aperte', 0)} di cui scadute {prev.get('scadute', 0)}"
        )
    sites = snap.get("siti") or []
    if sites:
        lines.append("- Sintesi per sito: " + "; ".join(
            f"{s.get('code')}: compliance {s.get('pct_compliant') if s.get('pct_compliant') is not None else 'n/d'}%, "
            + (f"rischi oltre soglia {s.get('rischi_oltre_soglia', 0)}, " if "rischi_oltre_soglia" in s
               else f"rischi critici {s.get('rischi_critici', 0)}, ")
            + f"incidenti aperti {s.get('incidenti_aperti', 0)}"
            for s in sites
        ))

    lines += ["", "ORDINE DEL GIORNO, DISCUSSIONE E DECISIONI"]
    items = review.agenda_items.prefetch_related("decisions")
    for item in items:
        title = ISO_AGENDA_TITLES.get(item.code) or item.title
        clause = ISO_AGENDA_CLAUSE.get(item.code)
        lines.append(f"* {clause + ') ' if clause else ''}{title}")
        lines.append(f"  Discussione: {item.discussion.strip()[:1500] or '(nessuna)'}")
        for dec in item.decisions.all():
            due = f" con scadenza {dec.due_date.isoformat()}" if dec.due_date else ""
            tipo = DECISION_LABELS.get(dec.decision_type, dec.decision_type)
            lines.append(f"  Decisione di tipo {tipo}{due}: {dec.description.strip()[:500]}")
    loose = review.actions.filter(agenda_item__isnull=True)
    for dec in loose:
        lines.append(f"* Decisione non associata a un punto: {dec.description.strip()[:500]}")

    language = LANGUAGE_NAMES.get(lang, LANGUAGE_NAMES["it"])
    lines += [
        "",
        "ISTRUZIONI",
        f"Scrivi in {language} la sintesi executive del verbale, 250-400 parole, in 3 o 4 paragrafi "
        "di testo semplice (niente titoli, elenchi puntati o markdown):",
        "1) giudizio complessivo sull'adeguatezza ed efficacia del SGSI;",
        "2) principali criticità emerse dai dati (compliance, rischi, incidenti, audit, KPI);",
        "3) esiti della riunione e decisioni prese, con eventuali scadenze;",
        "4) priorità per il periodo fino al prossimo riesame.",
        "Se un'informazione non è presente nei dati, non citarla.",
        "Scrivi in prosa scorrevole: non ricopiare le etichette fra parentesi quadre né i "
        "riferimenti a clausole di norma.",
    ]
    return "\n".join(lines)


def draft_executive_summary(review: ManagementReview, user, lang: str = "it") -> dict:
    """Genera una bozza IA della sintesi. Solleva `LlmUnavailable` / `ValueError`
    (IA non raggiungibile o non configurata), gestiti dalla view."""
    from apps.ai_engine.router import route
    from apps.plants.models import Plant

    from .review import ensure_full_review

    ensure_full_review(review)
    _ensure_editable(review)
    if not review.snapshot_generated_at:
        raise ValidationError(_("Generare lo snapshot dei dati prima di chiedere la sintesi all'IA."))

    pseudo = _PersonPseudonymizer()
    prompt = pseudo.apply(build_summary_prompt(review, lang))
    plant_ids = [review.plant_id] if review.plant_id else list(Plant.objects.values_list("pk", flat=True))

    result = route(
        task_type="review_summary",
        prompt=prompt,
        system=SYSTEM_PROMPT,
        user=user,
        entity_id=review.pk,
        module_source="M13",
        sanitize=True,
        plant_ids=plant_ids,
        max_tokens=1500,
        timeout=120,
    )
    text = pseudo.restore((result.get("text") or "").strip())
    if not text:
        raise ValidationError(_("L'IA non ha restituito alcun testo. Riprovare."))

    review.executive_summary_draft = text
    review.executive_summary_draft_meta = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "used_fallback": result.get("used_fallback", False),
        "interaction_id": result.get("interaction_id"),
        "generated_at": timezone.now().isoformat(),
        "lang": lang,
        "snapshot_generated_at": review.snapshot_generated_at.isoformat(),
    }
    review.save(update_fields=["executive_summary_draft", "executive_summary_draft_meta", "updated_at"])
    log_action(
        user=user,
        action_code="management_review.summary.ai_draft",
        level="L2",
        entity=review,
        payload={
            "review_id": str(review.pk),
            "model": f"{result.get('provider')}/{result.get('model')}",
            "interaction_id": result.get("interaction_id"),
        },
    )
    return review.executive_summary_draft_meta


def accept_executive_summary(review: ManagementReview, text: str, user) -> ManagementReview:
    """Salva la sintesi nel verbale. Se esiste una bozza IA, il testo accettato
    (eventualmente modificato) la consuma e l'interazione IA viene confermata."""
    from apps.ai_engine.router import confirm_output

    from .review import ensure_full_review

    ensure_full_review(review)
    _ensure_editable(review)
    text = (text or "").strip()
    draft = review.executive_summary_draft.strip()
    draft_meta = review.executive_summary_draft_meta or {}
    previous_meta = review.executive_summary_meta or {}

    if not text:
        review.executive_summary = ""
        review.executive_summary_meta = {}
    else:
        if draft:
            ai_meta = {
                "ai_assisted": True,
                "provider": draft_meta.get("provider"),
                "model": draft_meta.get("model"),
                "interaction_id": draft_meta.get("interaction_id"),
                "generated_at": draft_meta.get("generated_at"),
                "edited": text != draft,
            }
            if draft_meta.get("interaction_id"):
                confirm_output(draft_meta["interaction_id"], user, text)
        elif previous_meta.get("ai_assisted"):
            ai_meta = {**previous_meta, "edited": previous_meta.get("edited") or text != review.executive_summary}
        else:
            ai_meta = {"ai_assisted": False}
        review.executive_summary = text
        review.executive_summary_meta = {
            **{k: v for k, v in ai_meta.items() if k not in ("accepted_by", "accepted_by_name", "accepted_at")},
            "accepted_by": user.pk,
            "accepted_by_name": (f"{user.first_name} {user.last_name}".strip() or user.get_username()),
            "accepted_at": timezone.now().isoformat(),
        }

    review.executive_summary_draft = ""
    review.executive_summary_draft_meta = {}
    review.save(update_fields=[
        "executive_summary", "executive_summary_meta",
        "executive_summary_draft", "executive_summary_draft_meta", "updated_at",
    ])
    log_action(
        user=user,
        action_code="management_review.summary.accepted",
        level="L2",
        entity=review,
        payload={
            "review_id": str(review.pk),
            "ai_assisted": bool(review.executive_summary_meta.get("ai_assisted")),
            "edited": bool(review.executive_summary_meta.get("edited")),
            "cleared": not text,
        },
    )
    return review


def discard_summary_draft(review: ManagementReview, user) -> ManagementReview:
    from apps.ai_engine.router import ignore_output

    _ensure_editable(review)
    interaction_id = (review.executive_summary_draft_meta or {}).get("interaction_id")
    if interaction_id:
        ignore_output(interaction_id)
    review.executive_summary_draft = ""
    review.executive_summary_draft_meta = {}
    review.save(update_fields=["executive_summary_draft", "executive_summary_draft_meta", "updated_at"])
    log_action(
        user=user, action_code="management_review.summary.ai_discarded", level="L3", entity=review,
        payload={"review_id": str(review.pk)},
    )
    return review
