"""Modello neutro della relazione del riesame (verbale), condiviso da HTML e PDF.

Il documento segue l'ordine del giorno ISO 27001 §9.3.2: per ogni punto i dati
congelati pertinenti, la discussione e le decisioni. Tutti i valori sono testo
semplice NON ancora escapato: ci pensa il renderer.

Blocchi:
  {"type": "kpis", "items": [(label, value, tone)]}
  {"type": "table", "title", "headers", "rows", "more", "empty"}
      cella = str oppure {"text", "tone", "bold"}
  {"type": "paragraph", "label", "text"}
tone ∈ {None, "red", "orange", "green", "muted"}
"""
from django.utils import timezone

from ..agenda import ISO_AGENDA_CLAUSE, ISO_AGENDA_TITLES

TREATMENT = {"mitigare": "Mitigare", "accettare": "Accettare", "trasferire": "Trasferire", "evitare": "Evitare"}
DECISION_TYPE = {
    "miglioramento": "Miglioramento", "modifica_sgsi": "Modifica al SGSI", "risorse": "Risorse", "altro": "Altro",
}
FINDING_TYPE = {
    "major_nc": "NC maggiore", "minor_nc": "NC minore", "observation": "Osservazione", "opportunity": "Opportunità",
}
KPI_STATUS = {"critical": "Critico", "warning": "Attenzione", "ok": "OK", "no_data": "N/D"}
SEVERITY = {"bassa": "Bassa", "media": "Media", "alta": "Alta", "critica": "Critica"}
INC_STATUS = {"aperto": "Aperto", "in_analisi": "In analisi", "chiuso": "Chiuso"}
TASK_STATUS = {
    "aperto": "Aperto", "in_corso": "In corso", "completato": "Completato", "annullato": "Annullato",
    "scaduto": "Scaduto",
}
PDCA_PHASE = {"plan": "PLAN", "do": "DO", "check": "CHECK", "act": "ACT", "chiuso": "Chiuso", "archiviato": "Archiviato"}
ROLE = {
    "compliance_officer": "Compliance Officer", "risk_manager": "Risk Manager", "plant_manager": "Plant Manager",
    "control_owner": "Control Owner", "internal_auditor": "Auditor Interno", "external_auditor": "Auditor Esterno",
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
        return [{"type": "paragraph", "label": None, "text": "Primo riesame del perimetro: nessuna azione precedente."}]
    p = prev["riesame_precedente"]
    rows = [
        [
            a.get("description") or "—",
            _dash(a.get("owner")),
            {"text": fmt_date(a.get("due_date")), "tone": "red" if a.get("overdue") else None},
            {"text": "Chiusa" if a.get("status") == "chiuso" else ("Scaduta" if a.get("overdue") else "Aperta"),
             "tone": "green" if a.get("status") == "chiuso" else ("red" if a.get("overdue") else "orange")},
            f"{a.get('review_title')} ({fmt_date(a.get('review_date'))})",
        ]
        for a in prev.get("elenco", [])
    ]
    return [
        {"type": "paragraph", "label": None,
         "text": f"Riesame precedente: {p.get('title')} del {fmt_date(p.get('review_date'))}."},
        _kpis(("Azioni considerate", prev.get("totale", 0), None), ("Chiuse", prev.get("chiuse", 0), "green"),
              ("Aperte", prev.get("aperte", 0), "orange"), ("Scadute", prev.get("scadute", 0), "red")),
        _table(None, ["Azione", "Owner", "Scadenza", "Stato", "Riesame"], rows, prev.get("totale"),
               empty="Nessuna azione dai riesami precedenti"),
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
    blocks = [_table("Compliance per framework",
                     ["Framework", "Controlli", "% compliant", "Compliant", "Gap/parziali", "Non valutati",
                      "Evidenze scadute"], rows, empty="Nessun dato disponibile")]
    if gap_rows:
        blocks.append(_table("Controlli in gap (primi 5 per framework)", ["Framework", "Controllo", "Titolo"],
                             gap_rows, gap_total))
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
        _kpis(("KPI monitorati", k.get("totale", 0), None), ("Critici", counts.get("critical", 0), "red"),
              ("In attenzione", counts.get("warning", 0), "orange"), ("Senza dati", counts.get("no_data", 0), "muted")),
        _table("KPI fuori soglia", ["KPI", "Valore", "Stato", "Soglie att./crit.", "Settimana"], rows,
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
        _kpis(("Audit (12 mesi)", a.get("audit_12m", 0), None), ("NC maggiori aperte", a.get("nc_aperte_maggiori", 0), "red"),
              ("NC minori aperte", a.get("nc_aperte_minori", 0), "orange"), ("Finding scaduti", a.get("finding_scaduti", 0), "red")),
        _table("Audit degli ultimi 12 mesi", ["Audit", "Data", "Framework", "Readiness", "Finding"], audits,
               a.get("audit_12m")),
        _table("Non conformità aperte", ["Finding", "Tipo", "Audit", "Risposta entro"], ncs,
               a.get("nc_aperte_maggiori", 0) + a.get("nc_aperte_minori", 0)),
    ]


def _incident_blocks(snap) -> list:
    inc = snap.get("incidenti") or {}

    def rows(items):
        return [[i.get("title"), fmt_date(i.get("detected_at")), SEVERITY.get(i.get("severity"), _dash(i.get("severity"))),
                 INC_STATUS.get(i.get("status"), _dash(i.get("status")))] for i in items]

    headers = ["Incidente", "Rilevato il", "Gravità", "Stato"]
    return [
        _kpis(("Incidenti (12 mesi)", inc.get("totale_12m", 0), None), ("Notificati NIS2", inc.get("nis2_notificati", 0), "red"),
              ("Ancora aperti", inc.get("aperti", 0), "orange"), ("Chiusi senza RCA", inc.get("senza_rca", 0), "orange")),
        _table("Incidenti aperti", headers, rows(inc.get("elenco_aperti", [])), inc.get("aperti")),
        _table("Incidenti notificati NIS2 (12 mesi)", headers, rows(inc.get("elenco_nis2", [])), inc.get("nis2_notificati")),
    ]


def _improvement_status_blocks(snap) -> list:
    pdca, task = snap.get("pdca") or {}, snap.get("task") or {}
    return [
        _kpis(("Cicli PDCA aperti", pdca.get("aperti", 0), None), ("Fermi in PLAN >90gg", pdca.get("bloccati_plan_90gg", 0), "red"),
              ("PDCA chiusi (12 mesi)", pdca.get("chiusi_12m", 0), "green"), ("Task scaduti", task.get("scaduti", 0), "red")),
        _table("Cicli PDCA fermi in PLAN da oltre 90 giorni", ["Ciclo", "Aperto il"],
               [[c.get("title"), fmt_date(c.get("created_at"))] for c in pdca.get("elenco_bloccati", [])],
               pdca.get("bloccati_plan_90gg")),
        _table("Task scaduti (per priorità)", ["Task", "Priorità", "Scadenza", "Ruolo"],
               [[t.get("title"), SEVERITY.get(t.get("priority"), _dash(t.get("priority"))),
                 {"text": fmt_date(t.get("due_date")), "tone": "red"}, ROLE.get(t.get("assigned_role"), _dash(t.get("assigned_role")))]
                for t in task.get("elenco_scaduti", [])],
               task.get("scaduti")),
    ]


def _document_blocks(snap) -> list:
    d = snap.get("documenti") or {}

    def rows(items, key):
        return [[x.get("title"), _dash(x.get("owner")), fmt_date(x.get(key))] for x in items]

    blocks = [_kpis(("Documenti approvati", d.get("approvati", 0), None), ("In scadenza (90gg)", d.get("in_scadenza", 0), "orange"),
                    ("Documenti scaduti", d.get("scaduti", 0), "red"), ("Evidenze scadute", d.get("evidenze_scadute", 0), "red"))]
    if "elenco_scaduti" in d:
        blocks += [
            _table("Documenti scaduti", ["Documento", "Owner", "Revisione prevista"],
                   rows(d.get("elenco_scaduti", []), "review_due_date"), d.get("scaduti")),
            _table("Documenti in scadenza entro 90 giorni", ["Documento", "Owner", "Revisione prevista"],
                   rows(d.get("elenco_in_scadenza", []), "review_due_date"), d.get("in_scadenza")),
            _table(f"Documenti approvati dal {fmt_date(d.get('approvati_dal'))}", ["Documento", "Owner", "Approvato il"],
                   rows(d.get("elenco_approvati_periodo", []), "approved_at"), d.get("approvati_periodo")),
        ]
    return blocks


def _risk_blocks(snap) -> list:
    r = snap.get("rischi") or {}
    blocks = [_kpis(("Rischi critici", r.get("rosso", 0), "red"), ("Rischi medi", r.get("giallo", 0), "orange"),
                    ("Rischi bassi", r.get("verde", 0), "green"), ("Critici senza piano", r.get("senza_piano", 0), "red"))]
    if "top_critici" in r:
        blocks += [
            _table("Rischi critici (residuo più alto)",
                   ["Rischio", "Asset / processo", "Inerente → residuo", "Trattamento", "Owner", "Piano"],
                   [[x.get("name"), _dash(x.get("asset") or x.get("process")),
                     f"{_dash(x.get('inherent_score'))} → {_dash(x.get('score'))}",
                     TREATMENT.get(x.get("treatment"), _dash(x.get("treatment"))), _dash(x.get("owner")),
                     {"text": "Sì" if x.get("has_plan") else "No", "tone": None if x.get("has_plan") else "red", "bold": not x.get("has_plan")}]
                    for x in r.get("top_critici", [])],
                   r.get("rosso")),
            _table("Rischi accettati formalmente", ["Rischio", "Residuo", "Accettato da", "Scadenza accettazione"],
                   [[x.get("name"), _dash(x.get("score")), _dash(x.get("accepted_by")), fmt_date(x.get("acceptance_expiry"))]
                    for x in r.get("elenco_accettati", [])],
                   r.get("accettati_formalmente")),
        ]
    bcp = snap.get("bcp") or {}
    if bcp.get("processi_critici_senza_bcp"):
        blocks.append({"type": "paragraph", "label": "Continuità operativa",
                       "text": f"{bcp['processi_critici_senza_bcp']} processi critici senza piano BCP: "
                               + ", ".join(bcp.get("nomi", []))})
    return blocks


def _opportunity_blocks(snap) -> list:
    a = snap.get("audit") or {}
    items = a.get("elenco_opportunita", [])
    if not items:
        return []
    return [_table("Opportunità di miglioramento emerse dagli audit", ["Opportunità", "Audit", "Stato"],
                   [[x.get("title"), x.get("audit") or "—", "Aperta" if x.get("status") != "closed" else "Chiusa"]
                    for x in items],
                   a.get("opportunita_aperte"))]


DATA_BLOCKS = {
    "azioni_precedenti": lambda s: _previous_actions_blocks(s),
    "prestazioni": lambda s: (_compliance_blocks(s) + _kpi_blocks(s) + _audit_blocks(s) + _incident_blocks(s)
                              + _improvement_status_blocks(s) + _document_blocks(s)),
    "rischi": lambda s: _risk_blocks(s),
    "miglioramento": lambda s: _opportunity_blocks(s),
}


def _decision_rows(actions, with_item=False):
    rows = []
    for a in actions:
        links = []
        if a.task_id:
            links.append(f"Task: {TASK_STATUS.get(a.task.status, a.task.status)}")
        if a.pdca_cycle_id:
            links.append(f"PDCA: {PDCA_PHASE.get(a.pdca_cycle.fase_corrente, a.pdca_cycle.fase_corrente)}")
        row = [
            a.description,
            DECISION_TYPE.get(a.decision_type, a.decision_type),
            _user(a.owner) if a.owner_id else "—",
            fmt_date(a.due_date),
            {"text": "Chiusa" if a.status == "chiuso" else "Aperta", "tone": "green" if a.status == "chiuso" else None},
            ", ".join(links) or "—",
        ]
        rows.append(row)
    return rows


DECISION_HEADERS = ["Decisione", "Tipo", "Owner", "Scadenza", "Stato", "Collegamenti"]


def _alerts(snap) -> list[str]:
    r, bcp, d, pdca = snap.get("rischi", {}), snap.get("bcp", {}), snap.get("documenti", {}), snap.get("pdca", {})
    prev, audit = snap.get("azioni_precedenti") or {}, snap.get("audit") or {}
    out = []
    if r.get("senza_owner", 0) > 0:
        out.append(f"Ci sono {r['senza_owner']} rischi senza owner assegnato")
    if r.get("senza_piano", 0) > 0:
        out.append(f"{r['senza_piano']} rischi critici senza piano di mitigazione")
    if bcp.get("processi_critici_senza_bcp", 0) > 0:
        out.append(f"{bcp['processi_critici_senza_bcp']} processi critici senza piano BCP")
    if d.get("evidenze_scadute", 0) > 0:
        out.append(f"{d['evidenze_scadute']} evidenze scadute")
    if pdca.get("bloccati_plan_90gg", 0) > 0:
        out.append(f"{pdca['bloccati_plan_90gg']} cicli PDCA bloccati in fase PLAN da oltre 90 giorni")
    if prev.get("scadute", 0) > 0:
        out.append(f"{prev['scadute']} azioni dei riesami precedenti scadute e ancora aperte")
    if audit.get("nc_aperte_maggiori", 0) > 0:
        out.append(f"{audit['nc_aperte_maggiori']} non conformità maggiori aperte")
    return out


def build_report(review) -> dict:
    snap = review.snapshot_data
    if not snap:
        raise ValueError("Snapshot non ancora generato")

    attendees = ", ".join(_user(u) for u in review.attendees.all()) or "—"
    meta = [
        ("Titolo", review.title),
        ("Perimetro", review.plant.name if review.plant_id else "Intera organizzazione"),
        ("Data riunione", fmt_date(review.review_date)),
        ("Presieduto da", _user(review.chair) if review.chair_id else "—"),
        ("Partecipanti", attendees),
        ("Dati congelati il", fmt_date(snap.get("generated_at"))),
        ("Stato approvazione", {"approvato": "Approvato", "bozza": "Bozza"}.get(review.approval_status,
                                                                                   review.approval_status)),
        ("Prossimo riesame", fmt_date(review.next_review_date)),
    ]

    summary = None
    if review.executive_summary.strip():
        m = review.executive_summary_meta or {}
        if m.get("ai_assisted"):
            note = (f"Testo redatto con il supporto dell'intelligenza artificiale ({m.get('provider')}/{m.get('model')})"
                    f"{' e modificato' if m.get('edited') else ''}, verificato e accettato da "
                    f"{m.get('accepted_by_name') or '—'} il {fmt_date(m.get('accepted_at'))}.")
        else:
            note = f"Redatto da {m.get('accepted_by_name') or '—'} il {fmt_date(m.get('accepted_at'))}."
        summary = {"text": review.executive_summary, "note": note}

    sections = []
    sites = snap.get("siti") or []
    if sites:
        sections.append({"heading": "Quadro per sito", "blocks": [_table(
            None, ["Sito", "% compliant", "Rischi critici", "Incidenti aperti", "Task scaduti"],
            [[f"{s.get('code')} — {s.get('name')}",
              f"{s['pct_compliant']}%" if s.get("pct_compliant") is not None else "—",
              str(s.get("rischi_critici", 0)), str(s.get("incidenti_aperti", 0)), str(s.get("task_scaduti", 0))]
             for s in sites])]})

    actions = list(review.actions.all())
    agenda = list(review.agenda_items.all())
    if agenda:
        for item in agenda:
            clause = ISO_AGENDA_CLAUSE.get(item.code)
            title = ISO_AGENDA_TITLES.get(item.code) or item.title
            blocks = list(DATA_BLOCKS.get(item.code, lambda s: [])(snap))
            blocks.append({"type": "paragraph", "label": "Discussione",
                           "text": item.discussion.strip() or "Nessuna annotazione."})
            decisions = [a for a in actions if a.agenda_item_id == item.pk]
            if decisions:
                blocks.append(_table("Decisioni", DECISION_HEADERS, _decision_rows(decisions)))
            sections.append({"heading": f"{clause}) {title}" if clause else title, "blocks": blocks})
        loose = [a for a in actions if a.agenda_item_id is None]
        if loose:
            sections.append({"heading": "Altre decisioni", "blocks": [_table(None, DECISION_HEADERS, _decision_rows(loose))]})
    else:
        # Riesami approvati prima dell'ordine del giorno strutturato.
        blocks = []
        for code in ("azioni_precedenti", "prestazioni", "rischi", "miglioramento"):
            blocks += DATA_BLOCKS[code](snap)
        sections.append({"heading": "Dati del riesame", "blocks": blocks})
        sections.append({"heading": "Decisioni e azioni", "blocks": [
            _table(None, DECISION_HEADERS, _decision_rows(actions), empty="Nessuna azione registrata")]})

    # Riepilogo unico degli output §9.3.3, utile quando le decisioni sono
    # distribuite su più punti (altrimenti ripeterebbe la stessa tabella).
    if agenda and len({a.agenda_item_id for a in actions}) > 1:
        sections.append({"heading": "Riepilogo delle decisioni (output §9.3.3)",
                         "blocks": [_table(None, DECISION_HEADERS, _decision_rows(actions))]})

    approval = None
    if review.approval_status == "approvato" and review.approved_at:
        approval = {
            "by": _user(review.approved_by),
            "at": timezone.localtime(review.approved_at).strftime("%d/%m/%Y %H:%M"),
            "note": review.approval_note or "—",
        }

    return {
        "title": "Riesame di Direzione SGSI",
        "subtitle": "ISO/IEC 27001:2022 §9.3",
        "meta": meta,
        "summary": summary,
        "alerts": _alerts(snap),
        "sections": sections,
        "approval": approval,
        "footer": f"Documento generato dal sistema GRC il {timezone.localtime().strftime('%d/%m/%Y %H:%M')} — "
                  f"RISERVATO — Solo per uso interno",
    }
