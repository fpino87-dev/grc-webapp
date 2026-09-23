"""Modello neutro della relazione del riesame (verbale), condiviso da HTML e PDF.

Il documento segue l'ordine del giorno ISO 27001 §9.3.2: per ogni punto i dati
congelati pertinenti, la discussione e le decisioni. Tutti i valori sono testo
semplice NON ancora escapato: ci pensa il renderer.

Le etichette sono tradotte nella lingua di chi scarica il verbale
(`Accept-Language`): un sito francese o polacco riceve il proprio verbale, non
uno italiano. `gettext_lazy` risolve al momento del rendering, non all'import.

Blocchi:
  {"type": "kpis", "items": [(label, value, tone)]}
  {"type": "table", "title", "headers", "rows", "more", "empty"}
      cella = str oppure {"text", "tone", "bold"}
  {"type": "paragraph", "label", "text"}
tone ∈ {None, "red", "orange", "green", "muted"}
"""
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..agenda import ISO_AGENDA_CLAUSE, ISO_AGENDA_TITLES

TREATMENT = {"mitigare": _("Mitigare"), "accettare": _("Accettare"), "trasferire": _("Trasferire"),
             "evitare": _("Evitare")}
DECISION_TYPE = {
    "miglioramento": _("Miglioramento"), "modifica_sgsi": _("Modifica al SGSI"), "risorse": _("Risorse"),
    "obiettivo": _("Obiettivo di sicurezza"), "altro": _("Altro"),
}
FINDING_TYPE = {
    "major_nc": _("NC maggiore"), "minor_nc": _("NC minore"), "observation": _("Osservazione"),
    "opportunity": _("Opportunità"),
}
KPI_STATUS = {"critical": _("Critico"), "warning": _("Attenzione"), "ok": _("OK"), "no_data": _("N/D")}
SEVERITY = {"bassa": _("Bassa"), "media": _("Media"), "alta": _("Alta"), "critica": _("Critica")}
INC_STATUS = {"aperto": _("Aperto"), "in_analisi": _("In analisi"), "chiuso": _("Chiuso")}
TASK_STATUS = {
    "aperto": _("Aperto"), "in_corso": _("In corso"), "completato": _("Completato"),
    "annullato": _("Annullato"), "scaduto": _("Scaduto"),
}
PDCA_PHASE = {"plan": "PLAN", "do": "DO", "check": "CHECK", "act": "ACT", "chiuso": _("Chiuso"),
              "archiviato": _("Archiviato")}
ROLE = {
    "compliance_officer": _("Compliance Officer"), "risk_manager": _("Risk Manager"),
    "plant_manager": _("Plant Manager"), "control_owner": _("Control Owner"),
    "internal_auditor": _("Auditor Interno"), "external_auditor": _("Auditor Esterno"),
}
# Traiettoria di un obiettivo di sicurezza (§6.2): non è lo stato del record,
# è la lettura dell'andamento rispetto al target e alla scadenza.
OBJECTIVE_TRACK = {
    "in_linea": _("In linea"), "a_rischio": _("A rischio"), "mancato": _("Mancato"),
    "senza_misure": _("Senza misure"), "non_applicabile": _("—"),
}
DOC_STATUS = {
    "bozza": _("Bozza"), "revisione": _("In revisione"), "approvazione": _("In approvazione"),
    "approvato": _("Approvato"), "archiviato": _("Archiviato"),
}
DOC_TYPE = {
    "policy": _("Policy"), "procedura": _("Procedura"), "manuale": _("Manuale ISMS"),
    "contratto": _("Contratto/NDA"), "registro": _("Registro"), "altro": _("Altro"),
}
OBJECTIVE_STATUS = {
    "bozza": _("Bozza"), "attivo": _("Attivo"), "raggiunto": _("Raggiunto"),
    "non_raggiunto": _("Non raggiunto"), "sospeso": _("Sospeso"), "annullato": _("Annullato"),
}


def fmt_date(value) -> str:
    """ISO 'YYYY-MM-DD[T…]' o date → 'DD/MM/YYYY'."""
    if not value:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    try:
        y, m, d = str(value)[:10].split("-")
        return f"{d}/{m}/{y}"
    except ValueError:
        return str(value)


def _user(u) -> str:
    return (f"{u.first_name} {u.last_name}".strip() or u.email) if u else "—"


def _participant_row(p) -> list:
    role = {
        "presidente": _("Presidente"), "membro": _("Membro"),
        "segretario": _("Segretario"), "ospite": _("Ospite"),
    }.get(p.body_role, p.body_role)
    if p.is_chair and p.body_role != "presidente":
        role = f"{role} · {_('presiede')}"
    attendance = {
        "presente": _("Presente"), "assente": _("Assente"),
        "delegato": _("Delegato: %(name)s") % {"name": p.delegate_name},
    }.get(p.attendance, p.attendance)
    return [p.full_name, p.position or "—", role, attendance]


def _approval_lines(review) -> list:
    """Riquadro di approvazione: chi ha approvato e in che forma. In app, se
    ha approvato un componente dell'organo, compare lui con la qualifica; con
    delibera, gli estremi della delibera e chi l'ha registrata."""
    at = timezone.localtime(review.approved_at).strftime("%d/%m/%Y %H:%M")
    if review.approval_mode == "delibera":
        body = review.governing_body.name if review.governing_body_id else _("Organo di governo")
        lines = [
            (_("Approvato da"), body),
            (_("Delibera"), _("n. %(ref)s del %(date)s") % {
                "ref": review.approval_resolution_ref, "date": fmt_date(review.approval_resolution_date)}),
            (_("Registrata da"), f"{_user(review.approved_by)} — {at}"),
        ]
    else:
        m = review.approved_member
        who = (f"{m.full_name} — {m.position}" if m.position else m.full_name) if m else _user(review.approved_by)
        lines = [(_("Approvato da"), who), (_("Data"), at)]
    lines.append((_("Note"), review.approval_note or "—"))
    return lines


def _dash(v) -> str:
    return "—" if v in (None, "") else str(v)


def _table(title, headers, rows, total=None, empty=None):
    return {
        "type": "table", "title": title, "headers": headers, "rows": rows,
        "more": max((total or 0) - len(rows), 0) if total is not None else 0, "empty": empty,
    }


def _kpis(*items):
    return {"type": "kpis", "items": list(items)}


# ── Blocchi dati ──────────────────────────────────────────────────────────────

def _previous_actions_blocks(snap) -> list:
    prev = snap.get("azioni_precedenti")
    if prev is None:
        return []
    if not prev.get("riesame_precedente"):
        return [{"type": "paragraph", "label": None, "text": _("Primo riesame del perimetro: nessuna azione precedente.")}]
    p = prev["riesame_precedente"]
    rows = [
        [
            a.get("description") or "—",
            _dash(a.get("owner")),
            {"text": fmt_date(a.get("due_date")), "tone": "red" if a.get("overdue") else None},
            {"text": _("Chiusa") if a.get("status") == "chiuso" else (
                _("Scaduta") if a.get("overdue") else _("Aperta")),
             "tone": "green" if a.get("status") == "chiuso" else ("red" if a.get("overdue") else "orange")},
            f"{a.get('review_title')} ({fmt_date(a.get('review_date'))})",
        ]
        for a in prev.get("elenco", [])
    ]
    return [
        {"type": "paragraph", "label": None,
         "text": _("Riesame precedente: %(title)s del %(date)s.") % {
             "title": p.get("title"), "date": fmt_date(p.get("review_date"))}},
        _kpis((_("Azioni considerate"), prev.get("totale", 0), None),
              (_("Chiuse"), prev.get("chiuse", 0), "green"),
              (_("Aperte"), prev.get("aperte", 0), "orange"),
              (_("Scadute"), prev.get("scadute", 0), "red")),
        _table(None, [_("Azione"), _("Owner"), _("Scadenza"), _("Stato"), _("Riesame")], rows,
               prev.get("totale"), empty=_("Nessuna azione dai riesami precedenti")),
    ]


def _compliance_blocks(snap) -> list:
    fws = snap.get("frameworks") or {}
    rows, gap_rows, gap_total = [], [], 0
    for code, fw in fws.items():
        bs = fw.get("by_status", {})
        pct = fw.get("pct_compliant", 0)
        rows.append([
            {"text": f"{code} — {fw.get('framework_name', '')}", "bold": True},
            str(fw.get("total", 0)),
            {"text": f"{pct}%", "tone": "green" if pct >= 80 else "orange" if pct >= 60 else "red", "bold": True},
            str(bs.get("compliant", 0)),
            str(bs.get("gap", 0) + bs.get("parziale", 0)),
            str(bs.get("non_valutato", 0)),
            str(fw.get("expired_evidence_count", 0)),
        ])
        gaps = fw.get("gap_controls", [])[:5]
        gap_total += bs.get("gap", 0)
        for g in gaps:
            titles = g.get("titles") or {}
            gap_rows.append([code, g.get("control__external_id") or "—", titles.get("it") or titles.get("en") or ""])
    blocks = [_table(_("Compliance per framework"),
                     [_("Framework"), _("Controlli"), _("% compliant"), _("Compliant"), _("Gap/parziali"),
                      _("Non valutati"), _("Evidenze scadute")], rows, empty=_("Nessun dato disponibile"))]
    if gap_rows:
        blocks.append(_table(_("Controlli in gap (primi 5 per framework)"),
                             [_("Framework"), _("Controllo"), _("Titolo")], gap_rows, gap_total))
    return blocks


def _kpi_blocks(snap) -> list:
    k = snap.get("kpi")
    if not k:
        return []
    counts = k.get("status_counts") or {}
    rows = [
        [
            f"{i.get('name')}" + (f" ({i['plant_code']})" if i.get("plant_code") else ""),
            f"{_dash(i.get('value'))} {i.get('unit') or ''}".strip(),
            {"text": KPI_STATUS.get(i.get("status"), i.get("status")),
             "tone": "red" if i.get("status") == "critical" else "orange"},
            f"{_dash(i.get('threshold_warning'))} / {_dash(i.get('threshold_critical'))}",
            fmt_date(i.get("week_start")),
        ]
        for i in k.get("elenco_attenzione", [])
    ]
    return [
        _kpis((_("KPI monitorati"), k.get("totale", 0), None), (_("Critici"), counts.get("critical", 0), "red"),
              (_("In attenzione"), counts.get("warning", 0), "orange"),
              (_("Senza dati"), counts.get("no_data", 0), "muted")),
        _table(_("KPI fuori soglia"),
               [_("KPI"), _("Valore"), _("Stato"), _("Soglie att./crit."), _("Settimana")], rows,
               k.get("attenzione")),
    ]


def _audit_blocks(snap) -> list:
    a = snap.get("audit")
    if not a:
        return []
    audits = [
        [x.get("title"), fmt_date(x.get("audit_date")), _dash(x.get("framework")),
         f"{x['readiness_score']}%" if x.get("readiness_score") is not None else "—", str(x.get("findings", 0))]
        for x in a.get("elenco_audit", [])
    ]
    ncs = [
        [x.get("title"), {"text": FINDING_TYPE.get(x.get("finding_type"), x.get("finding_type")),
                          "tone": "red" if x.get("finding_type") == "major_nc" else "orange"},
         x.get("audit") or "—", {"text": fmt_date(x.get("response_deadline")), "tone": "red" if x.get("overdue") else None}]
        for x in a.get("elenco_nc_aperte", [])
    ]
    return [
        _kpis((_("Audit (12 mesi)"), a.get("audit_12m", 0), None),
              (_("NC maggiori aperte"), a.get("nc_aperte_maggiori", 0), "red"),
              (_("NC minori aperte"), a.get("nc_aperte_minori", 0), "orange"),
              (_("Finding scaduti"), a.get("finding_scaduti", 0), "red")),
        _table(_("Audit degli ultimi 12 mesi"),
               [_("Audit"), _("Data"), _("Framework"), _("Readiness"), _("Finding")], audits,
               a.get("audit_12m")),
        _table(_("Non conformità aperte"), [_("Finding"), _("Tipo"), _("Audit"), _("Risposta entro")], ncs,
               a.get("nc_aperte_maggiori", 0) + a.get("nc_aperte_minori", 0)),
    ]


def _incident_blocks(snap) -> list:
    inc = snap.get("incidenti") or {}

    def rows(items):
        return [[i.get("title"), fmt_date(i.get("detected_at")), SEVERITY.get(i.get("severity"), _dash(i.get("severity"))),
                 INC_STATUS.get(i.get("status"), _dash(i.get("status")))] for i in items]

    headers = [_("Incidente"), _("Rilevato il"), _("Gravità"), _("Stato")]
    return [
        _kpis((_("Incidenti (12 mesi)"), inc.get("totale_12m", 0), None),
              (_("Notificati NIS2"), inc.get("nis2_notificati", 0), "red"),
              (_("Ancora aperti"), inc.get("aperti", 0), "orange"),
              (_("Chiusi senza RCA"), inc.get("senza_rca", 0), "orange")),
        _table(_("Incidenti aperti"), headers, rows(inc.get("elenco_aperti", [])), inc.get("aperti")),
        _table(_("Incidenti notificati NIS2 (12 mesi)"), headers, rows(inc.get("elenco_nis2", [])),
               inc.get("nis2_notificati")),
    ]


def _improvement_status_blocks(snap) -> list:
    pdca, task = snap.get("pdca") or {}, snap.get("task") or {}
    return [
        _kpis((_("Cicli PDCA aperti"), pdca.get("aperti", 0), None),
              (_("Fermi in PLAN >90gg"), pdca.get("bloccati_plan_90gg", 0), "red"),
              (_("PDCA chiusi (12 mesi)"), pdca.get("chiusi_12m", 0), "green"),
              (_("Task scaduti"), task.get("scaduti", 0), "red")),
        _table(_("Cicli PDCA fermi in PLAN da oltre 90 giorni"), [_("Ciclo"), _("Aperto il")],
               [[c.get("title"), fmt_date(c.get("created_at"))] for c in pdca.get("elenco_bloccati", [])],
               pdca.get("bloccati_plan_90gg")),
        _table(_("Task scaduti (per priorità)"), [_("Task"), _("Priorità"), _("Scadenza"), _("Ruolo")],
               [[t.get("title"), SEVERITY.get(t.get("priority"), _dash(t.get("priority"))),
                 {"text": fmt_date(t.get("due_date")), "tone": "red"}, ROLE.get(t.get("assigned_role"), _dash(t.get("assigned_role")))]
                for t in task.get("elenco_scaduti", [])],
               task.get("scaduti")),
    ]


def approved_documents_ids(review) -> set:
    """Id dei documenti mandati in vigore con l'approvazione di questo riesame."""
    from apps.documents.models import DocumentApproval

    return {
        str(doc_id) for doc_id in DocumentApproval.objects.filter(
            review_id=review.pk, action="approve", deleted_at__isnull=True,
        ).values_list("document_id", flat=True)
    }


def _doc_label(item) -> str:
    code = item.get("document_code")
    return f"[{code}] {item.get('title')}" if code else str(item.get("title") or "")


def _document_blocks(snap, ctx=None) -> list:
    d = snap.get("documenti") or {}
    # Documenti approvati proprio in questa seduta: nei dati congelati
    # risultano ancora in lavorazione, ma il verbale deve dire com'è finita —
    # è un esito del riesame (§9.3.3), non un dato di partenza.
    approved_here = (ctx or {}).get("approved_in_review") or set()

    def rows(items, key):
        return [[x.get("title"), _dash(x.get("owner")), fmt_date(x.get(key))] for x in items]

    blocks = [_kpis((_("Documenti approvati"), d.get("approvati", 0), None),
                    (_("In scadenza (90gg)"), d.get("in_scadenza", 0), "orange"),
                    (_("Documenti scaduti"), d.get("scaduti", 0), "red"),
                    (_("Evidenze scadute"), d.get("evidenze_scadute", 0), "red"))]
    if "elenco_non_approvati" in d:
        blocks.append(_table(
            _("Documenti obbligatori non ancora approvati"),
            [_("Documento"), _("Tipo"), _("Stato"), _("Revisione"), _("Creato il")],
            [[_doc_label(x),
              DOC_TYPE.get(x.get("document_type"), _dash(x.get("document_type"))),
              {"text": _("Approvato in questa seduta"), "tone": "green", "bold": True}
              if str(x.get("id")) in approved_here
              else {"text": DOC_STATUS.get(x.get("status"), _dash(x.get("status"))), "tone": "orange"},
              _dash(x.get("version")), fmt_date(x.get("created_at"))]
             for x in d.get("elenco_non_approvati", [])],
            d.get("non_approvati_obbligatori"),
            empty=_("Tutti i documenti obbligatori del perimetro sono approvati."),
        ))
    if "elenco_scaduti" in d:
        doc_headers = [_("Documento"), _("Owner"), _("Revisione prevista")]
        blocks += [
            _table(_("Documenti scaduti"), doc_headers,
                   rows(d.get("elenco_scaduti", []), "review_due_date"), d.get("scaduti")),
            _table(_("Documenti in scadenza entro 90 giorni"), doc_headers,
                   rows(d.get("elenco_in_scadenza", []), "review_due_date"), d.get("in_scadenza")),
            _table(_("Documenti approvati dal %(date)s") % {"date": fmt_date(d.get("approvati_dal"))},
                   [_("Documento"), _("Owner"), _("Approvato il")],
                   rows(d.get("elenco_approvati_periodo", []), "approved_at"), d.get("approvati_periodo")),
        ]
    return blocks


def _risk_blocks(snap) -> list:
    r = snap.get("rischi") or {}
    blocks = [_kpis((_("Rischi critici"), r.get("rosso", 0), "red"),
                    (_("Rischi medi"), r.get("giallo", 0), "orange"),
                    (_("Rischi bassi"), r.get("verde", 0), "green"),
                    (_("Critici senza piano"), r.get("senza_piano", 0), "red"))]
    if "top_critici" in r:
        blocks += [
            _table(_("Rischi critici (residuo più alto)"),
                   [_("Rischio"), _("Asset / processo"), _("Inerente → residuo"), _("Trattamento"), _("Owner"),
                    _("Piano")],
                   [[x.get("name"), _dash(x.get("asset") or x.get("process")),
                     f"{_dash(x.get('inherent_score'))} → {_dash(x.get('score'))}",
                     TREATMENT.get(x.get("treatment"), _dash(x.get("treatment"))), _dash(x.get("owner")),
                     {"text": _("Sì") if x.get("has_plan") else _("No"),
                      "tone": None if x.get("has_plan") else "red", "bold": not x.get("has_plan")}]
                    for x in r.get("top_critici", [])],
                   r.get("rosso")),
            _table(_("Rischi accettati formalmente"),
                   [_("Rischio"), _("Residuo"), _("Accettato da"), _("Scadenza accettazione")],
                   [[x.get("name"), _dash(x.get("score")), _dash(x.get("accepted_by")), fmt_date(x.get("acceptance_expiry"))]
                    for x in r.get("elenco_accettati", [])],
                   r.get("accettati_formalmente")),
        ]
    bcp = snap.get("bcp") or {}
    if bcp.get("processi_critici_senza_bcp"):
        blocks.append({"type": "paragraph", "label": _("Continuità operativa"),
                       "text": _("%(n)s processi critici senza piano BCP: %(names)s") % {
                           "n": bcp["processi_critici_senza_bcp"], "names": ", ".join(bcp.get("nomi", []))}})
    return blocks


def _opportunity_blocks(snap) -> list:
    a = snap.get("audit") or {}
    items = a.get("elenco_opportunita", [])
    if not items:
        return []
    return [_table(_("Opportunità di miglioramento emerse dagli audit"),
                   [_("Opportunità"), _("Audit"), _("Stato")],
                   [[x.get("title"), x.get("audit") or "—",
                     _("Aperta") if x.get("status") != "closed" else _("Chiusa")]
                    for x in items],
                   a.get("opportunita_aperte"))]


def _objectives_blocks(snap) -> list:
    """§9.3.2 d4) — stato degli obiettivi di sicurezza.

    La tabella mostra partenza → valore attuale → target con la traiettoria,
    non solo il valore corrente: il punto del riesame non è sapere dove siamo,
    è sapere se arriveremo dove ci eravamo impegnati ad arrivare.
    """
    o = snap.get("obiettivi")
    if not o:
        return []  # riesami con snapshot generato prima di questa funzione
    tone = {"mancato": "red", "a_rischio": "orange", "in_linea": "green", "senza_misure": "muted"}
    rows = []
    for i in o.get("elenco", []):
        unit = i.get("unit") or ""
        rows.append([
            f"{i.get('code')} — {i.get('title')}" + (f" ({i['plant_code']})" if i.get("plant_code") else ""),
            f"{_dash(i.get('baseline_value'))} → {_dash(i.get('target_value'))} {unit}".strip(),
            f"{_dash(i.get('current_value'))} {unit}".strip(),
            {"text": f"{i['progress_pct']}%" if i.get("progress_pct") is not None else "—",
             "tone": tone.get(i.get("track"))},
            fmt_date(i.get("target_date")),
            {"text": OBJECTIVE_TRACK.get(i.get("track"), _dash(i.get("track"))),
             "tone": tone.get(i.get("track")), "bold": i.get("track") in ("mancato", "a_rischio")},
            ROLE.get(i.get("owner_role"), _dash(i.get("owner_role"))),
        ])
    return [
        _kpis((_("Obiettivi attivi"), o.get("attivi", 0), None),
              (_("Mancati o fuori traiettoria"), o.get("mancati", 0), "red"),
              (_("A rischio"), o.get("a_rischio", 0), "orange"),
              (_("Raggiunti (12 mesi)"), o.get("raggiunti", 0), "green")),
        _table(_("Obiettivi di sicurezza (§6.2)"),
               [_("Obiettivo"), _("Partenza → target"), _("Valore attuale"), _("Progresso"), _("Scadenza"),
                _("Traiettoria"), _("Responsabile")],
               rows, o.get("totale"), empty=_("Nessun obiettivo di sicurezza definito per questo perimetro.")),
    ]


DATA_BLOCKS = {
    "azioni_precedenti": lambda s, ctx: _previous_actions_blocks(s),
    "prestazioni": lambda s, ctx: (_compliance_blocks(s) + _kpi_blocks(s) + _objectives_blocks(s)
                                   + _audit_blocks(s) + _incident_blocks(s)
                                   + _improvement_status_blocks(s) + _document_blocks(s, ctx)),
    "rischi": lambda s, ctx: _risk_blocks(s),
    "miglioramento": lambda s, ctx: _opportunity_blocks(s),
}


def _decision_rows(actions, with_item=False):
    rows = []
    for a in actions:
        links = []
        if a.task_id:
            links.append(_("Task: %(status)s") % {"status": TASK_STATUS.get(a.task.status, a.task.status)})
        if a.pdca_cycle_id:
            links.append(_("PDCA: %(phase)s") % {
                "phase": PDCA_PHASE.get(a.pdca_cycle.fase_corrente, a.pdca_cycle.fase_corrente)})
        row = [
            a.description,
            DECISION_TYPE.get(a.decision_type, a.decision_type),
            _user(a.owner) if a.owner_id else "—",
            fmt_date(a.due_date),
            {"text": _("Chiusa") if a.status == "chiuso" else _("Aperta"),
             "tone": "green" if a.status == "chiuso" else None},
            ", ".join(links) or "—",
        ]
        rows.append(row)
    return rows


DECISION_HEADERS = [_("Decisione"), _("Tipo"), _("Owner"), _("Scadenza"), _("Stato"), _("Collegamenti")]


def _alerts(snap) -> list[str]:
    r, bcp, d, pdca = snap.get("rischi", {}), snap.get("bcp", {}), snap.get("documenti", {}), snap.get("pdca", {})
    prev, audit = snap.get("azioni_precedenti") or {}, snap.get("audit") or {}
    out = []
    if r.get("senza_owner", 0) > 0:
        out.append(_("Ci sono %(n)s rischi senza owner assegnato") % {"n": r["senza_owner"]})
    if r.get("senza_piano", 0) > 0:
        out.append(_("%(n)s rischi critici senza piano di mitigazione") % {"n": r["senza_piano"]})
    if bcp.get("processi_critici_senza_bcp", 0) > 0:
        out.append(_("%(n)s processi critici senza piano BCP") % {"n": bcp["processi_critici_senza_bcp"]})
    if d.get("evidenze_scadute", 0) > 0:
        out.append(_("%(n)s evidenze scadute") % {"n": d["evidenze_scadute"]})
    if pdca.get("bloccati_plan_90gg", 0) > 0:
        out.append(_("%(n)s cicli PDCA bloccati in fase PLAN da oltre 90 giorni")
                   % {"n": pdca["bloccati_plan_90gg"]})
    if prev.get("scadute", 0) > 0:
        out.append(_("%(n)s azioni dei riesami precedenti scadute e ancora aperte") % {"n": prev["scadute"]})
    if audit.get("nc_aperte_maggiori", 0) > 0:
        out.append(_("%(n)s non conformità maggiori aperte") % {"n": audit["nc_aperte_maggiori"]})
    obj = snap.get("obiettivi") or {}
    # Mancati e a rischio insieme: per la direzione sono lo stesso problema
    # (non arriveremo dove ci eravamo impegnati), a stadi diversi.
    off_track = obj.get("mancati", 0) + obj.get("a_rischio", 0)
    if off_track > 0:
        out.append(_("%(n)s obiettivi di sicurezza mancati o fuori traiettoria") % {"n": off_track})
    return out


def _scope_subtitle(review) -> str:
    """Framework realmente in perimetro, al posto della sola ISO 27001.

    Il riesame di direzione è uno solo e vale per tutti i sistemi di gestione
    adottati: intestarlo alla sola ISO 27001 dava un'informazione incompleta a
    un auditor TISAX o a un'autorità NIS2. La struttura dell'ordine del giorno
    resta quella di ISO 27001 §9.3.2 — è indicata dalle lettere di clausola sui
    singoli punti, dove serve all'auditor, senza intestare l'intero documento.
    """
    try:
        from apps.plants.services import get_active_frameworks

        # I codici e non i nomi completi: "TISAX — VDA ISA 6.0 Assessment Level 2
        # (High Protection Need)" ripetuto tre volte non sta in una riga di
        # intestazione e non aggiunge nulla a chi legge il verbale.
        codes = list(dict.fromkeys(fw.code for fw in get_active_frameworks(review.plant)))
    except Exception:  # nessun framework caricato: il verbale resta valido
        codes = []
    if not codes:
        return str(_("Riesame periodico dei sistemi di gestione"))
    shown, rest = codes[:5], len(codes) - 5
    line = " · ".join(shown)
    return f"{line} · +{rest}" if rest > 0 else line


OUTCOME = {"approvato": _("Approvato"), "rinviato": _("Rinviato"), "respinto": _("Respinto")}
OUTCOME_TONE = {"approvato": "green", "rinviato": "orange", "respinto": "red"}


def _version_label(version) -> str:
    if version is None:
        return "—"
    return version.version_label or f"v{version.version_number}"


def _outcome_state(item, review_approved: bool) -> dict:
    """Stato dell'applicazione dell'esito al documento, come cella di tabella."""
    if item.document_outcome_applied_at:
        return {"text": _("Applicato il %(date)s") % {"date": fmt_date(item.document_outcome_applied_at)},
                "tone": "green"}
    if item.document_outcome_error:
        return {"text": _("Non applicato: %(reason)s") % {"reason": item.document_outcome_error},
                "tone": "red", "bold": True}
    if not item.document_outcome:
        return {"text": _("Esito non registrato"), "tone": "muted"}
    if not review_approved:
        return {"text": _("Si applica all'approvazione del verbale"), "tone": "muted"}
    return {"text": "—", "tone": "muted"}


def _common_meta(review, chair) -> list:
    return [
        (_("Titolo"), review.title),
        (_("Perimetro"), review.plant.name if review.plant_id else _("Intera organizzazione")),
        (_("Organo"), review.governing_body.name if review.governing_body_id else "—"),
        (_("Data riunione"), fmt_date(review.review_date)),
        (_("Presieduto da"), chair.full_name if chair else "—"),
    ]


def _report_frame(review, *, title, subtitle, meta, summary, alerts, sections) -> dict:
    """Logo, approvazione e piè di pagina comuni ai due tipi di verbale."""
    from apps.plants.services import plant_logo

    approval = None
    if review.approval_status == "approvato" and review.approved_at:
        approval = {"lines": _approval_lines(review)}
    logo = plant_logo(review.report_logo_plant) if review.report_logo_plant_id else None
    return {
        "logo": {"data": logo[0], "mime": logo[1]} if logo else None,
        "title": title,
        "subtitle": subtitle,
        "meta": meta,
        "summary": summary,
        "alerts": alerts,
        "sections": sections,
        "approval": approval,
        "footer": _("Documento generato dal sistema GRC il %(when)s — RISERVATO — Solo per uso interno") % {
            "when": timezone.localtime().strftime("%d/%m/%Y %H:%M")},
    }


def build_targeted_report(review) -> dict:
    """Verbale del riesame mirato: la seduta dell'organo sui punti in ordine
    del giorno, con i documenti esaminati e il loro esito. Nessun dato
    congelato né punti §9.3.2: il sottotitolo dichiara che non è il riesame
    periodico."""
    participants = list(review.participants.all())
    chair = next((p for p in participants if p.is_chair), None)
    approved = review.approval_status == "approvato"
    meta = _common_meta(review, chair) + [
        (_("Stato approvazione"), {"approvato": _("Approvato"), "bozza": _("Bozza")}.get(
            review.approval_status, review.approval_status)),
    ]

    agenda = list(review.agenda_items.all())
    actions = list(review.actions.all())
    doc_items = [i for i in agenda if i.document_id]

    sections = []
    if participants:
        sections.append({"heading": _("Partecipanti"), "blocks": [_table(
            None, [_("Nome"), _("Qualifica"), _("Ruolo"), _("Presenza")],
            [_participant_row(p) for p in participants])]})
    if doc_items:
        sections.append({"heading": _("Documenti esaminati"), "blocks": [_table(
            None, [_("Documento"), _("Revisione esaminata"), _("Esito"), _("Applicazione")],
            [[i.title, _version_label(i.document_version),
              {"text": OUTCOME.get(i.document_outcome, "—"), "tone": OUTCOME_TONE.get(i.document_outcome),
               "bold": True},
              _outcome_state(i, approved)] for i in doc_items])]})

    for item in agenda:
        blocks = []
        if item.document_id:
            heading = _("Documento: %(title)s") % {"title": item.title}
            blocks.append({"type": "paragraph", "label": _("Esito"), "text": _(
                "%(outcome)s — revisione esaminata %(version)s"
            ) % {"outcome": OUTCOME.get(item.document_outcome, _("non registrato")),
                 "version": _version_label(item.document_version)}})
        else:
            heading = item.title
        blocks.append({"type": "paragraph", "label": _("Discussione"),
                       "text": item.discussion.strip() or _("Nessuna annotazione.")})
        decisions = [a for a in actions if a.agenda_item_id == item.pk]
        if decisions:
            blocks.append(_table(_("Decisioni"), DECISION_HEADERS, _decision_rows(decisions)))
        sections.append({"heading": heading, "blocks": blocks})
    loose = [a for a in actions if a.agenda_item_id is None]
    if loose:
        sections.append({"heading": _("Altre decisioni"),
                         "blocks": [_table(None, DECISION_HEADERS, _decision_rows(loose))]})

    alerts = [
        _("%(title)s: esito «%(outcome)s» non applicato — %(reason)s") % {
            "title": i.title, "outcome": OUTCOME.get(i.document_outcome, i.document_outcome),
            "reason": i.document_outcome_error}
        for i in doc_items if i.document_outcome_error
    ]
    return _report_frame(
        review,
        title=_("Riesame mirato"),
        subtitle=_("Riunione dell'organo su punti specifici. Non sostituisce il riesame di direzione "
                   "periodico (ISO/IEC 27001 §9.3)."),
        meta=meta, summary=None, alerts=alerts, sections=sections,
    )


def build_report(review) -> dict:
    if review.is_targeted:
        return build_targeted_report(review)
    snap = review.snapshot_data
    if not snap:
        raise ValueError("Snapshot non ancora generato")

    participants = list(review.participants.all())
    chair = next((p for p in participants if p.is_chair), None)
    meta = _common_meta(review, chair) + [
        (_("Dati congelati il"), fmt_date(snap.get("generated_at"))),
        (_("Stato approvazione"), {"approvato": _("Approvato"), "bozza": _("Bozza")}.get(
            review.approval_status, review.approval_status)),
        (_("Prossimo riesame"), fmt_date(review.next_review_date)),
    ]

    summary = None
    if review.executive_summary.strip():
        m = review.executive_summary_meta or {}
        if m.get("ai_assisted"):
            # La trasparenza che serve al lettore è *che* il testo è assistito
            # dall'IA e *chi* l'ha verificato e fatto proprio. Fornitore e
            # modello sono dettaglio tecnico: restano nei metadati della sintesi
            # e nell'audit trail, dove un auditor può risalirci, senza occupare
            # il verbale che va in direzione.
            note = (_("Testo redatto con il supporto dell'intelligenza artificiale%(edited)s, "
                      "verificato e accettato da %(who)s il %(when)s.") % {
                "edited": _(" e modificato") if m.get("edited") else "",
                "who": m.get("accepted_by_name") or "—", "when": fmt_date(m.get("accepted_at"))})
        else:
            note = _("Redatto da %(who)s il %(when)s.") % {
                "who": m.get("accepted_by_name") or "—", "when": fmt_date(m.get("accepted_at"))}
        summary = {"text": review.executive_summary, "note": note}

    sections = []
    if participants:
        sections.append({"heading": _("Partecipanti"), "blocks": [_table(
            None, [_("Nome"), _("Qualifica"), _("Ruolo"), _("Presenza")],
            [_participant_row(p) for p in participants])]})
    sites = snap.get("siti") or []
    if sites:
        sections.append({"heading": _("Quadro per sito"), "blocks": [_table(
            None, [_("Sito"), _("% compliant"), _("Rischi critici"), _("Incidenti aperti"), _("Task scaduti")],
            [[f"{s.get('code')} — {s.get('name')}",
              f"{s['pct_compliant']}%" if s.get("pct_compliant") is not None else "—",
              str(s.get("rischi_critici", 0)), str(s.get("incidenti_aperti", 0)), str(s.get("task_scaduti", 0))]
             for s in sites])]})

    actions = list(review.actions.all())
    agenda = list(review.agenda_items.all())
    data_ctx = {"approved_in_review": approved_documents_ids(review)}
    if agenda:
        for item in agenda:
            clause = ISO_AGENDA_CLAUSE.get(item.code)
            title = ISO_AGENDA_TITLES.get(item.code) or item.title
            blocks = list(DATA_BLOCKS.get(item.code, lambda s, ctx: [])(snap, data_ctx))
            blocks.append({"type": "paragraph", "label": _("Discussione"),
                           "text": item.discussion.strip() or _("Nessuna annotazione.")})
            # Trasparenza (AI Act art. 50): il lettore del verbale deve sapere
            # quali testi sono assistiti dall'IA e chi li ha fatti propri.
            discussion_meta = item.discussion_meta or {}
            if item.discussion.strip() and discussion_meta.get("ai_assisted"):
                blocks.append({"type": "paragraph", "label": None, "text": _(
                    "Testo redatto con il supporto dell'intelligenza artificiale%(edited)s, "
                    "verificato e accettato da %(who)s il %(when)s."
                ) % {
                    "edited": _(" e modificato") if discussion_meta.get("edited") else "",
                    "who": discussion_meta.get("accepted_by_name") or "—",
                    "when": fmt_date(discussion_meta.get("accepted_at")),
                }})
            decisions = [a for a in actions if a.agenda_item_id == item.pk]
            if decisions:
                blocks.append(_table(_("Decisioni"), DECISION_HEADERS, _decision_rows(decisions)))
            sections.append({"heading": f"{clause}) {title}" if clause else title, "blocks": blocks})
        loose = [a for a in actions if a.agenda_item_id is None]
        if loose:
            sections.append({"heading": _("Altre decisioni"),
                             "blocks": [_table(None, DECISION_HEADERS, _decision_rows(loose))]})
    else:
        # Riesami approvati prima dell'ordine del giorno strutturato.
        blocks = []
        for code in ("azioni_precedenti", "prestazioni", "rischi", "miglioramento"):
            blocks += DATA_BLOCKS[code](snap, data_ctx)
        sections.append({"heading": _("Dati del riesame"), "blocks": blocks})
        sections.append({"heading": _("Decisioni e azioni"), "blocks": [
            _table(None, DECISION_HEADERS, _decision_rows(actions), empty=_("Nessuna azione registrata"))]})

    # Riepilogo unico degli output §9.3.3, utile quando le decisioni sono
    # distribuite su più punti (altrimenti ripeterebbe la stessa tabella).
    if agenda and len({a.agenda_item_id for a in actions}) > 1:
        sections.append({"heading": _("Riepilogo delle decisioni"),
                         "blocks": [_table(None, DECISION_HEADERS, _decision_rows(actions))]})

    return _report_frame(
        review, title=_("Riesame di Direzione SGSI"), subtitle=_scope_subtitle(review),
        meta=meta, summary=summary, alerts=_alerts(snap), sections=sections,
    )
