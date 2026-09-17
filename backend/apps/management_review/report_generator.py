"""Genera HTML della relazione CISO per il riesame di direzione."""

from html import escape

from django.utils import timezone

TREATMENT_LABELS = {
    "mitigare": "Mitigare",
    "accettare": "Accettare",
    "trasferire": "Trasferire",
    "evitare": "Evitare",
}


def _e(value, default="—") -> str:
    """Escape HTML: titoli, nomi e note sono testo libero inserito dagli utenti."""
    if value is None or value == "":
        return default
    return escape(str(value))


def _date(iso_value) -> str:
    """'2026-09-17[T…]' → '17/09/2026'."""
    if not iso_value:
        return "—"
    y, m, d = str(iso_value)[:10].split("-")
    return f"{d}/{m}/{y}"


def _more(total, shown) -> str:
    rest = (total or 0) - shown
    return f"<p class='more'>… e altri {rest}</p>" if rest > 0 else ""


def _table(headers, rows, empty="Nessun elemento") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    if not rows:
        return f"<table><tr>{head}</tr><tr><td colspan='{len(headers)}'>{empty}</td></tr></table>"
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def generate_review_report(review) -> str:
    snap = review.snapshot_data
    if not snap:
        raise ValueError("Snapshot non ancora generato")

    plant_name = _e(review.plant.name) if review.plant else "Organizzazione"

    def _user(u):
        return _e(f"{u.first_name} {u.last_name}".strip() or u.email)

    chair_name = _user(review.chair) if review.chair else "—"
    attendees = ", ".join(_user(u) for u in review.attendees.all()) or "—"

    # ── 1. Compliance ──
    fw_rows = ""
    gap_blocks = ""
    for code, fw in snap.get("frameworks", {}).items():
        by_status = fw.get("by_status", {})
        gap = by_status.get("gap", 0)
        parziale = by_status.get("parziale", 0)
        non_val = by_status.get("non_valutato", 0)
        pct = fw.get("pct_compliant", 0)
        color = "green" if pct >= 80 else "orange" if pct >= 60 else "red"
        fw_rows += f"""
        <tr>
          <td><strong>{_e(code)}</strong> — {_e(fw.get("framework_name"), "")}</td>
          <td>{fw.get("total", 0)}</td>
          <td style="color:{color};font-weight:bold">{pct}%</td>
          <td>{by_status.get("compliant", 0)}</td>
          <td>{gap + parziale}</td>
          <td>{non_val}</td>
          <td>{fw.get("expired_evidence_count", 0)}</td>
        </tr>"""
        gaps = fw.get("gap_controls", [])[:5]
        if gaps:
            items = "".join(
                f"<li><strong>{_e(g.get('control__external_id'))}</strong> "
                f"{_e((g.get('titles') or {}).get('it') or (g.get('titles') or {}).get('en'), '')}</li>"
                for g in gaps
            )
            gap_blocks += f"<p class='sub'>Controlli in gap — {_e(code)}</p><ul>{items}</ul>{_more(gap, len(gaps))}"

    rischi = snap.get("rischi", {})
    doc_snap = snap.get("documenti", {})
    inc = snap.get("incidenti", {})
    pdca = snap.get("pdca", {})
    bcp = snap.get("bcp", {})
    task = snap.get("task", {})

    # ── 2. Documenti ──
    def _doc_rows(items, date_key):
        return [[_e(d.get("title")), _e(d.get("owner")), _date(d.get(date_key))] for d in items]

    docs_detail = ""
    if "elenco_scaduti" in doc_snap:
        exp = doc_snap.get("elenco_scaduti", [])
        soon = doc_snap.get("elenco_in_scadenza", [])
        recent = doc_snap.get("elenco_approvati_periodo", [])
        docs_detail = (
            "<p class='sub'>Documenti scaduti</p>"
            + _table(["Documento", "Owner", "Revisione prevista"], _doc_rows(exp, "review_due_date"))
            + _more(doc_snap.get("scaduti"), len(exp))
            + "<p class='sub'>In scadenza entro 90 giorni</p>"
            + _table(["Documento", "Owner", "Revisione prevista"], _doc_rows(soon, "review_due_date"))
            + _more(doc_snap.get("in_scadenza"), len(soon))
            + f"<p class='sub'>Approvati dal {_date(doc_snap.get('approvati_dal'))}</p>"
            + _table(["Documento", "Owner", "Approvato il"], _doc_rows(recent, "approved_at"))
            + _more(doc_snap.get("approvati_periodo"), len(recent))
        )

    # ── 3. Rischi ──
    risks_detail = ""
    if "top_critici" in rischi:
        top = rischi.get("top_critici", [])
        top_rows = [
            [
                _e(r.get("name")),
                _e(r.get("asset") or r.get("process")),
                f"{_e(r.get('inherent_score'))} → <strong style='color:red'>{_e(r.get('score'))}</strong>",
                _e(TREATMENT_LABELS.get(r.get("treatment"), r.get("treatment"))),
                _e(r.get("owner")),
                "Sì" if r.get("has_plan") else "<strong style='color:red'>No</strong>",
            ]
            for r in top
        ]
        accepted = rischi.get("elenco_accettati", [])
        acc_rows = [
            [_e(r.get("name")), _e(r.get("score")), _e(r.get("accepted_by")), _date(r.get("acceptance_expiry"))]
            for r in accepted
        ]
        risks_detail = (
            "<p class='sub'>Rischi critici (residuo più alto)</p>"
            + _table(["Rischio", "Asset / processo", "Inerente → residuo", "Trattamento", "Owner", "Piano"], top_rows)
            + _more(rischi.get("rosso"), len(top))
            + "<p class='sub'>Rischi accettati formalmente</p>"
            + _table(["Rischio", "Residuo", "Accettato da", "Scadenza accettazione"], acc_rows)
            + _more(rischi.get("accettati_formalmente"), len(accepted))
        )

    # ── 4. Incidenti ──
    def _inc_rows(items):
        return [[_e(i.get("title")), _date(i.get("detected_at")), _e(i.get("severity")), _e(i.get("status"))] for i in items]

    inc_detail = ""
    if "elenco_aperti" in inc:
        open_i = inc.get("elenco_aperti", [])
        nis2_i = inc.get("elenco_nis2", [])
        headers = ["Incidente", "Rilevato il", "Gravità", "Stato"]
        inc_detail = (
            "<p class='sub'>Incidenti aperti</p>" + _table(headers, _inc_rows(open_i)) + _more(inc.get("aperti"), len(open_i))
            + "<p class='sub'>Notificati NIS2 (12 mesi)</p>" + _table(headers, _inc_rows(nis2_i))
            + _more(inc.get("nis2_notificati"), len(nis2_i))
        )

    # ── 5. PDCA e task ──
    pdca_detail = ""
    if "elenco_bloccati" in pdca:
        blocked = pdca.get("elenco_bloccati", [])
        overdue = task.get("elenco_scaduti", [])
        pdca_detail = (
            "<p class='sub'>Cicli PDCA fermi in PLAN da oltre 90 giorni</p>"
            + _table(["Ciclo", "Aperto il"], [[_e(c.get("title")), _date(c.get("created_at"))] for c in blocked])
            + _more(pdca.get("bloccati_plan_90gg"), len(blocked))
            + "<p class='sub'>Task scaduti (per priorità)</p>"
            + _table(
                ["Task", "Priorità", "Scadenza", "Ruolo"],
                [[_e(t.get("title")), _e(t.get("priority")), _date(t.get("due_date")), _e(t.get("assigned_role"))] for t in overdue],
            )
            + _more(task.get("scaduti"), len(overdue))
        )

    # ── 6. Delibere e azioni ──
    action_rows = [
        [
            _e(a.description),
            _user(a.owner) if a.owner else "—",
            _date(a.due_date.isoformat() if a.due_date else None),
            "Chiusa" if a.status == "chiuso" else "Aperta",
        ]
        for a in review.actions.all()
    ]

    alert_blocks = ""
    if rischi.get("senza_owner", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ Ci sono {rischi['senza_owner']} rischi senza owner assegnato</div>"
    if rischi.get("senza_piano", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ {rischi['senza_piano']} rischi critici senza piano di mitigazione</div>"
    if bcp.get("processi_critici_senza_bcp", 0) > 0:
        nomi = ", ".join(_e(n) for n in bcp.get("nomi", []))
        alert_blocks += f"<div class='alert'>⚠️ {bcp['processi_critici_senza_bcp']} processi critici senza piano BCP: {nomi}</div>"
    if doc_snap.get("evidenze_scadute", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ {doc_snap['evidenze_scadute']} evidenze scadute collegate a controlli compliant</div>"
    if pdca.get("bloccati_plan_90gg", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ {pdca['bloccati_plan_90gg']} cicli PDCA bloccati in fase PLAN da oltre 90 giorni</div>"

    approval_block = ""
    if review.approval_status == "approvato" and review.approved_by and review.approved_at:
        approval_block = f"""
        <div style="border:2px solid green;padding:16px;margin-top:32px;border-radius:8px">
          <strong style="color:green">✓ RIESAME APPROVATO</strong><br>
          Approvato da: {_user(review.approved_by)}<br>
          Data: {review.approved_at.strftime('%d/%m/%Y %H:%M')}<br>
          Note: {_e(review.approval_note)}
        </div>"""

    review_date_str = review.review_date.strftime('%d/%m/%Y') if review.review_date else "—"
    generated_at = _e(snap.get("generated_at", "")[:16].replace("T", " "))

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Riesame di Direzione — {_e(review.title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ font-size: 20px; border-bottom: 2px solid #1e40af; padding-bottom: 8px; color: #1e40af; }}
    h2 {{ font-size: 14px; color: #1e40af; margin-top: 24px; border-left: 4px solid #1e40af; padding-left: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px; }}
    th {{ background: #1e40af; color: white; padding: 6px 8px; text-align: left; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; }}
    tr:nth-child(even) {{ background: #f9fafb; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 12px 0; }}
    .kpi {{ background: #f0f4ff; border-radius: 6px; padding: 10px; text-align: center; }}
    .kpi-value {{ font-size: 22px; font-weight: bold; color: #1e40af; }}
    .kpi-label {{ font-size: 10px; color: #6b7280; margin-top: 2px; }}
    .alert {{ background: #fef2f2; border: 1px solid #fca5a5; padding: 8px 12px; border-radius: 4px; margin: 4px 0; font-size: 11px; }}
    .sub {{ font-weight: bold; margin: 14px 0 0; font-size: 11px; color: #374151; }}
    .more {{ font-size: 10px; color: #6b7280; margin: -8px 0 8px; }}
    ul {{ margin: 4px 0 8px; padding-left: 18px; font-size: 11px; }}
    @media print {{ body {{ margin: 0; }} }}
  </style>
</head>
<body>

<h1>Riesame di Direzione ISMS</h1>

<table style="margin-bottom:20px">
  <tr><td><strong>Titolo:</strong></td><td>{_e(review.title)}</td><td><strong>Sito:</strong></td><td>{plant_name}</td></tr>
  <tr><td><strong>Data riunione:</strong></td><td>{review_date_str}</td><td><strong>Presieduto da:</strong></td><td>{chair_name}</td></tr>
  <tr><td><strong>Partecipanti:</strong></td><td colspan="3">{attendees}</td></tr>
  <tr><td><strong>Snapshot generato:</strong></td><td>{generated_at}</td><td><strong>Stato approvazione:</strong></td><td>{_e(review.approval_status.upper())}</td></tr>
</table>

{('<h2>⚠️ Alert</h2>' + alert_blocks) if alert_blocks else ''}

<h2>1. Stato Compliance per Framework</h2>
<table>
  <tr><th>Framework</th><th>Totale controlli</th><th>% Compliant</th><th>Compliant</th><th>Gap/Parziale</th><th>Non valutati</th><th>Evidenze scadute</th></tr>
  {fw_rows if fw_rows else '<tr><td colspan="7">Nessun dato disponibile</td></tr>'}
</table>
{gap_blocks}

<h2>2. Documenti e Evidenze</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{doc_snap.get("approvati", 0)}</div><div class="kpi-label">Documenti approvati</div></div>
  <div class="kpi"><div class="kpi-value">{doc_snap.get("in_scadenza", 0)}</div><div class="kpi-label">In scadenza (90gg)</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{doc_snap.get("scaduti", 0)}</div><div class="kpi-label">Documenti scaduti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{doc_snap.get("evidenze_scadute", 0)}</div><div class="kpi-label">Evidenze scadute</div></div>
</div>
{docs_detail}

<h2>3. Profilo di Rischio</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value" style="color:red">{rischi.get("rosso", 0)}</div><div class="kpi-label">Rischi critici</div></div>
  <div class="kpi"><div class="kpi-value" style="color:orange">{rischi.get("giallo", 0)}</div><div class="kpi-label">Rischi medi</div></div>
  <div class="kpi"><div class="kpi-value" style="color:green">{rischi.get("verde", 0)}</div><div class="kpi-label">Rischi bassi</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{rischi.get("senza_piano", 0)}</div><div class="kpi-label">Critici senza piano</div></div>
</div>
{risks_detail}

<h2>4. Incidenti (ultimi 12 mesi)</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{inc.get("totale_12m", 0)}</div><div class="kpi-label">Totale incidenti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{inc.get("nis2_notificati", 0)}</div><div class="kpi-label">Notificati NIS2</div></div>
  <div class="kpi"><div class="kpi-value">{inc.get("aperti", 0)}</div><div class="kpi-label">Ancora aperti</div></div>
  <div class="kpi"><div class="kpi-value">{inc.get("senza_rca", 0)}</div><div class="kpi-label">Chiusi senza RCA</div></div>
</div>
{inc_detail}

<h2>5. PDCA e Miglioramento Continuo</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{pdca.get("aperti", 0)}</div><div class="kpi-label">Cicli aperti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{pdca.get("bloccati_plan_90gg", 0)}</div><div class="kpi-label">Bloccati in PLAN &gt;90gg</div></div>
  <div class="kpi"><div class="kpi-value" style="color:green">{pdca.get("chiusi_12m", 0)}</div><div class="kpi-label">Chiusi ultimi 12m</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{task.get("scaduti", 0)}</div><div class="kpi-label">Task scaduti</div></div>
</div>
{pdca_detail}

<h2>6. Delibere e Azioni</h2>
{_table(["Azione", "Owner", "Scadenza", "Stato"], action_rows, empty="Nessuna azione registrata")}

{approval_block}

<hr style="margin-top:40px;border-color:#e5e7eb">
<p style="font-size:10px;color:#9ca3af;text-align:center">
  Documento generato automaticamente dal sistema GRC —
  {timezone.now().strftime('%d/%m/%Y %H:%M')} —
  RISERVATO — Solo per uso interno
</p>

</body>
</html>"""
