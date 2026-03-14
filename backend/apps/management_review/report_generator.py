"""Genera HTML della relazione CISO per il riesame di direzione."""

from django.utils import timezone


def generate_review_report(review) -> str:
    snap = review.snapshot_data
    if not snap:
        raise ValueError("Snapshot non ancora generato")

    plant_name = review.plant.name if review.plant else "Organizzazione"
    chair_name = (
        f"{review.chair.first_name} {review.chair.last_name}".strip()
        if review.chair else "—"
    )

    # Sezione framework
    fw_rows = ""
    for code, fw in snap.get("frameworks", {}).items():
        gap = fw.get("by_status", {}).get("gap", 0)
        parziale = fw.get("by_status", {}).get("parziale", 0)
        non_val = fw.get("by_status", {}).get("non_valutato", 0)
        pct = fw.get("pct_compliant", 0)
        color = "green" if pct >= 80 else "orange" if pct >= 60 else "red"
        fw_rows += f"""
        <tr>
          <td><strong>{code}</strong> — {fw.get("framework_name", "")}</td>
          <td>{fw.get("total", 0)}</td>
          <td style="color:{color};font-weight:bold">{pct}%</td>
          <td>{fw.get("by_status", {}).get("compliant", 0)}</td>
          <td>{gap + parziale}</td>
          <td>{non_val}</td>
          <td>{fw.get("expired_evidence_count", 0)}</td>
        </tr>"""

    # Rischi per owner
    owner_rows = ""
    for o in snap.get("risks_by_owner", []):
        name = f"{o.get('owner__first_name', '')} {o.get('owner__last_name', '')}".strip() or o.get("owner__email", "—")
        owner_rows += f"<tr><td>{name}</td><td>{o.get('totale', 0)}</td><td style='color:red'>{o.get('rossi', 0)}</td></tr>"

    rischi = snap.get("rischi", {})
    doc_snap = snap.get("documenti", {})
    inc = snap.get("incidenti", {})
    pdca = snap.get("pdca", {})
    bcp = snap.get("bcp", {})
    task = snap.get("task", {})

    alert_blocks = ""
    if rischi.get("senza_owner", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ Ci sono {rischi['senza_owner']} rischi senza owner assegnato</div>"
    if rischi.get("senza_piano", 0) > 0:
        alert_blocks += f"<div class='alert'>⚠️ {rischi['senza_piano']} rischi critici senza piano di mitigazione</div>"
    if bcp.get("processi_critici_senza_bcp", 0) > 0:
        nomi = ", ".join(bcp.get("nomi", []))
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
          Approvato da: {review.approved_by.first_name} {review.approved_by.last_name}<br>
          Data: {review.approved_at.strftime('%d/%m/%Y %H:%M')}<br>
          Note: {review.approval_note or "—"}
        </div>"""

    review_date_str = review.review_date.strftime('%d/%m/%Y') if review.review_date else "—"
    generated_at = snap.get("generated_at", "")[:16].replace("T", " ")

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Riesame di Direzione — {review.title}</title>
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
    @media print {{ body {{ margin: 0; }} }}
  </style>
</head>
<body>

<h1>Riesame di Direzione ISMS</h1>

<table style="margin-bottom:20px">
  <tr><td><strong>Titolo:</strong></td><td>{review.title}</td><td><strong>Sito:</strong></td><td>{plant_name}</td></tr>
  <tr><td><strong>Data riunione:</strong></td><td>{review_date_str}</td><td><strong>Presieduto da:</strong></td><td>{chair_name}</td></tr>
  <tr><td><strong>Snapshot generato:</strong></td><td>{generated_at}</td><td><strong>Stato approvazione:</strong></td><td>{review.approval_status.upper()}</td></tr>
</table>

{('<h2>⚠️ Alert</h2>' + alert_blocks) if alert_blocks else ''}

<h2>1. Stato Compliance per Framework</h2>
<table>
  <tr><th>Framework</th><th>Totale controlli</th><th>% Compliant</th><th>Compliant</th><th>Gap/Parziale</th><th>Non valutati</th><th>Evidenze scadute</th></tr>
  {fw_rows if fw_rows else '<tr><td colspan="7">Nessun dato disponibile</td></tr>'}
</table>

<h2>2. Documenti e Evidenze</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{doc_snap.get("approvati", 0)}</div><div class="kpi-label">Documenti approvati</div></div>
  <div class="kpi"><div class="kpi-value">{doc_snap.get("in_scadenza", 0)}</div><div class="kpi-label">In scadenza (90gg)</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{doc_snap.get("scaduti", 0)}</div><div class="kpi-label">Documenti scaduti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{doc_snap.get("evidenze_scadute", 0)}</div><div class="kpi-label">Evidenze scadute</div></div>
</div>

<h2>3. Profilo di Rischio</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value" style="color:red">{rischi.get("rosso", 0)}</div><div class="kpi-label">Rischi critici</div></div>
  <div class="kpi"><div class="kpi-value" style="color:orange">{rischi.get("giallo", 0)}</div><div class="kpi-label">Rischi medi</div></div>
  <div class="kpi"><div class="kpi-value" style="color:green">{rischi.get("verde", 0)}</div><div class="kpi-label">Rischi bassi</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{rischi.get("senza_piano", 0)}</div><div class="kpi-label">Critici senza piano</div></div>
</div>

<h2>4. Rischi per Owner</h2>
<table>
  <tr><th>Owner</th><th>Totale rischi</th><th>Rischi critici</th></tr>
  {owner_rows if owner_rows else "<tr><td colspan='3'>Nessun owner assegnato</td></tr>"}
</table>

<h2>5. Incidenti (ultimi 12 mesi)</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{inc.get("totale_12m", 0)}</div><div class="kpi-label">Totale incidenti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{inc.get("nis2_notificati", 0)}</div><div class="kpi-label">Notificati NIS2</div></div>
  <div class="kpi"><div class="kpi-value">{inc.get("aperti", 0)}</div><div class="kpi-label">Ancora aperti</div></div>
  <div class="kpi"><div class="kpi-value">{inc.get("senza_rca", 0)}</div><div class="kpi-label">Chiusi senza RCA</div></div>
</div>

<h2>6. PDCA e Miglioramento Continuo</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-value">{pdca.get("aperti", 0)}</div><div class="kpi-label">Cicli aperti</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{pdca.get("bloccati_plan_90gg", 0)}</div><div class="kpi-label">Bloccati in PLAN &gt;90gg</div></div>
  <div class="kpi"><div class="kpi-value" style="color:green">{pdca.get("chiusi_12m", 0)}</div><div class="kpi-label">Chiusi ultimi 12m</div></div>
  <div class="kpi"><div class="kpi-value" style="color:red">{task.get("scaduti", 0)}</div><div class="kpi-label">Task scaduti</div></div>
</div>

<h2>7. Delibere e Azioni</h2>
<p>Le delibere e le azioni di miglioramento sono registrate nel sistema GRC e collegate a task con owner e scadenza.</p>

{approval_block}

<hr style="margin-top:40px;border-color:#e5e7eb">
<p style="font-size:10px;color:#9ca3af;text-align:center">
  Documento generato automaticamente dal sistema GRC —
  {timezone.now().strftime('%d/%m/%Y %H:%M')} —
  RISERVATO — Solo per uso interno
</p>

</body>
</html>"""
