"""Bozza IA della discussione dei punti all'ordine del giorno (M13 + M20).

Stesse regole della sintesi executive (CLAUDE.md #9, AI Act art. 50): al
modello arrivano solo i dati congelati nello snapshot pertinenti al punto, con
i nomi delle persone pseudonimizzati; la bozza resta separata dal verbale
finché una persona non la accetta, anche modificata; i metadati registrano
modello e validatore, così la relazione può dichiararlo.

La differenza dalla sintesi è il perimetro: qui si scrive **un punto** — la
discussione che porta ai dati di quel punto — non il quadro d'insieme.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action

from ..agenda import ISO_AGENDA_CLAUSE, ISO_AGENDA_TITLES
from ..models import ReviewAgendaItem
from .summary import LANGUAGE_NAMES, _PersonPseudonymizer, _fmt_list

SYSTEM_PROMPT = (
    "Sei un consulente esperto di sistemi di gestione della sicurezza delle informazioni. "
    "Redigi la discussione di UN punto all'ordine del giorno del verbale di un riesame di "
    "direzione. Usa esclusivamente i dati forniti: non inventare numeri, nomi, date o "
    "decisioni, e non proporre decisioni come se fossero già state prese — le decisioni le "
    "assume la direzione. Se i dati per il punto sono assenti, dillo in una riga e indica "
    "quali informazioni servono. I segnaposto tra parentesi quadre (es. [PERSONA_1]) vanno "
    "riportati identici; le altre annotazioni fra parentesi quadre sono etichette di "
    "servizio e non vanno ricopiate nel testo."
)


def _lines_compliance(snap) -> list[str]:
    out = []
    for code, fw in (snap.get("frameworks") or {}).items():
        by = fw.get("by_status", {})
        out.append(
            f"- {code}: {fw.get('pct_compliant', 0)}% conforme "
            f"({by.get('compliant', 0)}/{fw.get('total', 0)}), gap {by.get('gap', 0)}, "
            f"evidenze scadute {fw.get('expired_evidence_count', 0)}"
        )
    return out


def _lines_documenti(snap) -> list[str]:
    d = snap.get("documenti") or {}
    if not d:
        return []
    out = [
        f"- Documenti: approvati {d.get('approvati', 0)}, scaduti {d.get('scaduti', 0)}, "
        f"in scadenza a 90 giorni {d.get('in_scadenza', 0)}, approvati nel periodo "
        f"{d.get('approvati_periodo', 0)}; evidenze scadute {d.get('evidenze_scadute', 0)}"
    ]
    pending = d.get("elenco_non_approvati") or []
    if pending:
        out.append(
            f"- Documenti obbligatori non ancora approvati ({d.get('non_approvati_obbligatori', 0)}): "
            + _fmt_list(pending, lambda x: f"{x.get('title')} ({x.get('status')})")
        )
    return out


def _lines_kpi(snap) -> list[str]:
    k = snap.get("kpi") or {}
    if not k:
        return []
    out = [f"- KPI monitorati: {k.get('totale', 0)}, fuori soglia {k.get('attenzione', 0)}"]
    att = _fmt_list(
        k.get("elenco_attenzione"),
        lambda x: f"{x.get('name')} {x.get('value')}{x.get('unit') or ''} ({x.get('status')})",
    )
    if att:
        out.append(f"  KPI in allarme: {att}")
    return out


def _lines_obiettivi(snap) -> list[str]:
    o = snap.get("obiettivi") or {}
    if not o:
        return []
    out = [
        f"- Obiettivi di sicurezza: attivi {o.get('attivi', 0)}, mancati o fuori traiettoria "
        f"{o.get('mancati', 0)}, a rischio {o.get('a_rischio', 0)}, raggiunti {o.get('raggiunti', 0)}"
    ]
    items = _fmt_list(
        o.get("elenco"),
        lambda x: f"{x.get('title')} ({x.get('track')}, valore {x.get('current_value')} su {x.get('target_value')})",
    )
    if items:
        out.append(f"  Dettaglio: {items}")
    return out


def _lines_audit(snap) -> list[str]:
    a = snap.get("audit") or {}
    if not a:
        return []
    out = [
        f"- Audit negli ultimi 12 mesi: {a.get('audit_12m', 0)}; non conformità aperte "
        f"maggiori {a.get('nc_aperte_maggiori', 0)}, minori {a.get('nc_aperte_minori', 0)}, "
        f"osservazioni {a.get('osservazioni_aperte', 0)}, scadute {a.get('finding_scaduti', 0)}"
    ]
    nc = _fmt_list(a.get("elenco_nc_aperte"), lambda x: f"{x.get('title')} ({x.get('finding_type')})")
    if nc:
        out.append(f"  Non conformità aperte: {nc}")
    return out


def _lines_incidenti(snap) -> list[str]:
    i = snap.get("incidenti") or {}
    if not i:
        return []
    return [
        f"- Incidenti negli ultimi 12 mesi: {i.get('totale_12m', 0)}, aperti {i.get('aperti', 0)}, "
        f"notificabili NIS2 {i.get('nis2_notificati', 0)}, chiusi senza analisi delle cause "
        f"{i.get('senza_rca', 0)}"
    ]


def _lines_task(snap) -> list[str]:
    t = snap.get("task") or {}
    p = snap.get("pdca") or {}
    out = []
    if t:
        out.append(f"- Attività scadute {t.get('scaduti', 0)}, critiche aperte {t.get('critici_aperti', 0)}")
    if p:
        out.append(
            f"- Cicli di miglioramento aperti {p.get('aperti', 0)}, fermi in pianificazione da oltre "
            f"90 giorni {p.get('bloccati_plan_90gg', 0)}, chiusi nei 12 mesi {p.get('chiusi_12m', 0)}"
        )
    return out


def _lines_rischi(snap) -> list[str]:
    r = snap.get("rischi") or {}
    if not r:
        return []
    out = [
        f"- Rischi: critici {r.get('rosso', 0)} (senza piano {r.get('senza_piano', 0)}), medi "
        f"{r.get('giallo', 0)}, bassi {r.get('verde', 0)}, accettati formalmente "
        f"{r.get('accettati_formalmente', 0)}, senza responsabile {r.get('senza_owner', 0)}"
    ]
    top = _fmt_list(r.get("top_critici"), lambda x: f"{x.get('name')} (residuo {x.get('score')})")
    if top:
        out.append(f"  Rischi critici principali: {top}")
    bcp = snap.get("bcp") or {}
    if bcp.get("processi_critici_senza_bcp"):
        out.append(f"- Processi critici senza piano di continuità: {bcp['processi_critici_senza_bcp']}")
    return out


def _lines_azioni_precedenti(snap) -> list[str]:
    a = snap.get("azioni_precedenti") or {}
    if not a or not a.get("riesame_precedente"):
        return ["- Primo riesame del perimetro: nessuna azione precedente da verificare."]
    prev = a["riesame_precedente"]
    out = [
        f"- Riesame precedente: {prev.get('title')} del {prev.get('review_date')}",
        f"- Azioni: totali {a.get('totale', 0)}, aperte {a.get('aperte', 0)}, scadute "
        f"{a.get('scadute', 0)}, chiuse {a.get('chiuse', 0)}",
    ]
    items = _fmt_list(
        a.get("elenco"),
        lambda x: f"{x.get('description')} (stato {x.get('status')}{', in ritardo' if x.get('overdue') else ''})",
    )
    if items:
        out.append(f"  Dettaglio: {items}")
    return out


def _lines_miglioramento(snap) -> list[str]:
    out = _lines_task(snap)
    opp = _fmt_list((snap.get("audit") or {}).get("elenco_opportunita"), lambda x: x.get("title"))
    if opp:
        out.append(f"- Opportunità rilevate negli audit: {opp}")
    return out


def _lines_contesto(snap) -> list[str]:
    out = []
    siti = snap.get("siti") or []
    if siti:
        out.append("- Quadro per sito: " + _fmt_list(
            siti,
            lambda s: f"{s.get('code')} conformità {s.get('pct_compliant')}%, rischi critici "
                      f"{s.get('rischi_critici')}, incidenti aperti {s.get('incidenti_aperti')}",
        ))
    out += _lines_compliance(snap)
    return out


# Dati pertinenti a ciascun punto dell'ordine del giorno ISO 27001 §9.3.2.
AGENDA_DATA = {
    "azioni_precedenti": [_lines_azioni_precedenti],
    "contesto": [_lines_contesto],
    "parti_interessate": [],
    "prestazioni": [_lines_compliance, _lines_kpi, _lines_obiettivi, _lines_audit,
                    _lines_incidenti, _lines_documenti, _lines_task],
    "feedback_parti": [],
    "rischi": [_lines_rischi],
    "miglioramento": [_lines_miglioramento],
}

# Cosa deve contenere la discussione, punto per punto.
AGENDA_GUIDANCE = {
    "azioni_precedenti": "verifica dello stato delle azioni decise nei riesami precedenti, "
                         "con quelle rimaste aperte o in ritardo e il loro impatto.",
    "contesto": "cambiamenti nei fattori esterni e interni rilevanti per il sistema di "
                "gestione (organizzazione, siti, tecnologie, quadro normativo).",
    "parti_interessate": "cambiamenti nelle esigenze e aspettative delle parti interessate "
                         "(clienti, autorità, fornitori, personale).",
    "prestazioni": "andamento delle prestazioni di sicurezza: conformità, indicatori, "
                   "obiettivi, esiti degli audit, non conformità, incidenti, documentazione.",
    "feedback_parti": "riscontri ricevuti dalle parti interessate nel periodo.",
    "rischi": "esito della valutazione del rischio e stato del piano di trattamento, "
              "con i rischi critici e quelli privi di piano o di responsabile.",
    "miglioramento": "opportunità di miglioramento continuo emerse nel periodo.",
}


def _ensure_editable(item: ReviewAgendaItem) -> None:
    if item.review.approval_status == "approvato":
        raise ValidationError(_("Il riesame è approvato: la discussione non è più modificabile."))


def build_agenda_prompt(item: ReviewAgendaItem, lang: str = "it") -> str:
    review = item.review
    snap = review.snapshot_data or {}
    clause = ISO_AGENDA_CLAUSE.get(item.code)
    title = str(ISO_AGENDA_TITLES.get(item.code) or item.title or "")

    lines = [
        f"Riesame: {review.title}",
        f"Data riunione: {review.review_date.isoformat() if review.review_date else '—'}",
        f"Perimetro: {'sito ' + review.plant.name if review.plant_id else 'intera organizzazione'}",
        f"Dati congelati il: {(snap.get('generated_at') or '')[:10]}",
        "",
        f"PUNTO ALL'ORDINE DEL GIORNO{f' ({clause})' if clause else ''}: {title}",
        f"Oggetto del punto: {AGENDA_GUIDANCE.get(item.code, 'punto aggiunto dall’organizzazione.')}",
        "",
        "DATI CONGELATI PERTINENTI",
    ]
    data_lines = []
    for fn in AGENDA_DATA.get(item.code, []):
        data_lines += fn(snap)
    lines += data_lines or ["- Nessun dato strutturato in piattaforma per questo punto."]

    decisions = [a for a in review.actions.all() if a.agenda_item_id == item.pk]
    if decisions:
        lines += ["", "DECISIONI GIÀ REGISTRATE SU QUESTO PUNTO"]
        lines += [f"- {d.description} (scadenza {d.due_date or '—'})" for d in decisions[:10]]

    if item.discussion.strip():
        lines += ["", "TESTO GIÀ PRESENTE NEL VERBALE (da migliorare, non da contraddire)",
                  item.discussion.strip()[:2000]]

    lines += [
        "",
        f"ISTRUZIONI: scrivi in {LANGUAGE_NAMES.get(lang, 'italiano')} da 80 a 180 parole di "
        "testo semplice (niente titoli, elenchi puntati o markdown), come verbalizzazione "
        "della discussione di questo punto: che cosa dicono i dati, quali criticità "
        "emergono e quali aspetti la direzione deve valutare. Non attribuire affermazioni a "
        "persone e non dare per prese decisioni che non sono elencate sopra.",
    ]
    return "\n".join(lines)


def draft_agenda_discussion(item: ReviewAgendaItem, user, lang: str = "it") -> dict:
    """Bozza IA della discussione di un punto. Solleva `LlmUnavailable` /
    `ValueError` (IA non raggiungibile o non configurata), gestiti dalla view."""
    from apps.ai_engine.router import route
    from apps.plants.models import Plant

    review = item.review
    _ensure_editable(item)
    if not review.snapshot_generated_at:
        raise ValidationError(
            _("Generare lo snapshot dei dati prima di chiedere all'IA la discussione dei punti.")
        )

    pseudo = _PersonPseudonymizer()
    prompt = pseudo.apply(build_agenda_prompt(item, lang))
    plant_ids = [review.plant_id] if review.plant_id else list(Plant.objects.values_list("pk", flat=True))

    result = route(
        task_type="review_agenda_item",
        prompt=prompt,
        system=SYSTEM_PROMPT,
        user=user,
        entity_id=item.pk,
        module_source="M13",
        sanitize=True,
        plant_ids=plant_ids,
        max_tokens=800,
        timeout=120,
    )
    text = pseudo.restore((result.get("text") or "").strip())
    if not text:
        raise ValidationError(_("L'IA non ha restituito alcun testo. Riprovare."))

    item.discussion_draft = text
    item.discussion_draft_meta = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "used_fallback": result.get("used_fallback", False),
        "interaction_id": result.get("interaction_id"),
        "generated_at": timezone.now().isoformat(),
        "lang": lang,
        "snapshot_generated_at": review.snapshot_generated_at.isoformat(),
    }
    item.save(update_fields=["discussion_draft", "discussion_draft_meta", "updated_at"])
    log_action(
        user=user,
        action_code="management_review.agenda.ai_draft",
        level="L2",
        entity=item,
        payload={
            "review_id": str(review.pk),
            "agenda_code": item.code,
            "model": f"{result.get('provider')}/{result.get('model')}",
            "interaction_id": result.get("interaction_id"),
        },
    )
    return item.discussion_draft_meta


def accept_agenda_discussion(item: ReviewAgendaItem, text: str, user) -> ReviewAgendaItem:
    """Porta la discussione nel verbale. Se viene da una bozza IA, il testo
    accettato (anche modificato) la consuma e conferma l'interazione."""
    from apps.ai_engine.router import confirm_output

    _ensure_editable(item)
    text = (text or "").strip()
    draft = item.discussion_draft.strip()
    draft_meta = item.discussion_draft_meta or {}
    previous_meta = item.discussion_meta or {}

    if not text:
        item.discussion = ""
        item.discussion_meta = {}
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
            ai_meta = {**previous_meta, "edited": previous_meta.get("edited") or text != item.discussion}
        else:
            ai_meta = {"ai_assisted": False}
        item.discussion = text
        item.discussion_meta = {
            **{k: v for k, v in ai_meta.items() if k not in ("accepted_by", "accepted_by_name", "accepted_at")},
            "accepted_by": user.pk,
            "accepted_by_name": f"{user.first_name} {user.last_name}".strip() or user.email,
            "accepted_at": timezone.now().isoformat(),
        }

    item.discussion_draft = ""
    item.discussion_draft_meta = {}
    item.save(update_fields=[
        "discussion", "discussion_meta", "discussion_draft", "discussion_draft_meta", "updated_at",
    ])
    log_action(
        user=user,
        action_code="management_review.agenda.discussion_accepted",
        level="L2",
        entity=item,
        payload={
            "review_id": str(item.review_id),
            "agenda_code": item.code,
            "ai_assisted": bool((item.discussion_meta or {}).get("ai_assisted")),
            "edited": bool((item.discussion_meta or {}).get("edited")),
        },
    )
    return item


def discard_agenda_draft(item: ReviewAgendaItem, user) -> ReviewAgendaItem:
    """Scarta la bozza IA senza portarla nel verbale."""
    _ensure_editable(item)
    if item.discussion_draft:
        item.discussion_draft = ""
        item.discussion_draft_meta = {}
        item.save(update_fields=["discussion_draft", "discussion_draft_meta", "updated_at"])
        log_action(
            user=user,
            action_code="management_review.agenda.ai_draft_discarded",
            level="L1",
            entity=item,
            payload={"review_id": str(item.review_id), "agenda_code": item.code},
        )
    return item
