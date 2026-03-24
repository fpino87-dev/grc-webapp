import html as html_module
from datetime import timedelta

from django.utils import timezone

from apps.plants.models import CSIRT_BY_COUNTRY

from .models import ENISA_INCIDENT_CATEGORIES, Incident, NIS2Configuration, NIS2Notification


def _e(value) -> str:
    """Escape HTML per prevenire XSS nel documento generato."""
    if value is None:
        return "—"
    return html_module.escape(str(value))


def classify_significance(incident: Incident) -> bool:
    """Classificazione automatica significativita NIS2 Art.23."""
    if incident.significance_override is not None:
        return incident.significance_override

    config = NIS2Configuration.objects.filter(plant=incident.plant).first()
    threshold_users = config.threshold_users if config else 100
    threshold_hours = config.threshold_hours if config else 4.0
    threshold_eur = config.threshold_financial if config else 100000

    criteria = [
        incident.cross_border_impact,
        incident.critical_infrastructure_impact,
        incident.personal_data_involved,
        (incident.affected_users_count or 0) >= threshold_users,
        (incident.service_disruption_hours or 0) >= threshold_hours,
        (incident.financial_impact_eur or 0) >= threshold_eur,
    ]
    return any(criteria)


def set_nis2_deadlines(incident: Incident) -> Incident:
    """Imposta scadenze T+24/T+72/T+1m in base al perimetro NIS2 del plant."""
    t0 = incident.detected_at
    entity_type = incident.plant.nis2_scope if incident.plant else "importante"

    if entity_type == "essenziale":
        incident.early_warning_deadline = t0 + timedelta(hours=24)

    incident.formal_notification_deadline = t0 + timedelta(hours=72)
    incident.final_report_deadline = (t0 + timedelta(days=30)).date()

    incident.save(
        update_fields=[
            "early_warning_deadline",
            "formal_notification_deadline",
            "final_report_deadline",
            "updated_at",
        ]
    )
    return incident


def get_csirt_for_plant(plant) -> dict:
    """Ritorna i metadati CSIRT per il paese del plant."""
    country_code = plant.country if plant else "IT"
    return CSIRT_BY_COUNTRY.get(
        country_code,
        {
            "name": "CSIRT Nazionale",
            "portal": "",
            "email": "",
            "country": country_code,
        },
    )


def generate_nis2_document(incident: Incident, notification_type: str, user) -> str:
    """Genera documento HTML per notifica NIS2 verso CSIRT competente."""
    plant = incident.plant
    config = NIS2Configuration.objects.filter(plant=plant).first()
    csirt = get_csirt_for_plant(plant)
    entity_type = plant.nis2_scope if plant else "importante"
    now_str = timezone.now().strftime("%d/%m/%Y %H:%M")
    detected = incident.detected_at.strftime("%d/%m/%Y %H:%M") if incident.detected_at else "—"

    cat_label = next(
        (c[1] for c in ENISA_INCIDENT_CATEGORIES if c[0] == incident.incident_category),
        incident.incident_category or "—",
    )

    doc_titles = {
        "early_warning": "Early Warning — Notifica Preliminare",
        "formal_notification": "Notifica Formale di Incidente NIS2",
        "final_report": "Report Finale di Incidente NIS2",
        "update": "Aggiornamento Notifica Incidente NIS2",
    }
    doc_title = doc_titles.get(notification_type, "Notifica NIS2")
    deadline_map = {
        "early_warning": incident.early_warning_deadline,
        "formal_notification": incident.formal_notification_deadline,
        "final_report": incident.final_report_deadline,
    }
    deadline = deadline_map.get(notification_type)
    deadline_str = (
        deadline.strftime("%d/%m/%Y %H:%M")
        if deadline and hasattr(deadline, "strftime")
        else (str(deadline) if deadline else "—")
    )

    legal_name = config.legal_entity_name if config and config.legal_entity_name else (plant.name if plant else "—")
    legal_vat = config.legal_entity_vat if config and config.legal_entity_vat else "—"
    sector = config.nis2_sector if config and config.nis2_sector else "Manifattura"
    contact_name = config.internal_contact_name if config else "—"
    contact_email = config.internal_contact_email if config else "—"
    contact_phone = config.internal_contact_phone if config else "—"

    impact_rows = ""
    if incident.affected_users_count is not None:
        impact_rows += (
            f"<tr><td>Utenti/sistemi colpiti</td><td>{incident.affected_users_count}</td></tr>"
        )
    if incident.service_disruption_hours is not None:
        impact_rows += (
            f"<tr><td>Durata interruzione</td><td>{incident.service_disruption_hours} ore</td></tr>"
        )
    if incident.financial_impact_eur is not None:
        impact_rows += (
            f"<tr><td>Impatto finanziario stimato</td><td>EUR {incident.financial_impact_eur:,.2f}</td></tr>"
        )
    impact_rows += (
        f"<tr><td>Dati personali coinvolti</td><td>{'Si — verificare obbligo notifica GDPR' if incident.personal_data_involved else 'No'}</td></tr>"
        f"<tr><td>Impatto cross-border</td><td>{'Si' if incident.cross_border_impact else 'No'}</td></tr>"
        f"<tr><td>Infrastrutture critiche</td><td>{'Si' if incident.critical_infrastructure_impact else 'No'}</td></tr>"
    )

    assets_preview = ", ".join([_e(a.name) for a in incident.assets.all()[:5]]) or "Da specificare"

    extra_sections = ""
    if notification_type == "early_warning":
        extra_sections = f"""
<div class="section">
  <h2>EARLY WARNING — Avviso Preliminare</h2>
  <p class="note">
    Questo documento costituisce la notifica preliminare (Early Warning) prevista
    dall'Art. 23(1) NIS2 per entita essenziali.
  </p>
  <table>
    <tr><td>Incidente rilevato</td><td>{_e(detected)}</td></tr>
    <tr><td>Classificazione preliminare</td><td>{_e(cat_label)}</td></tr>
    <tr><td>Impatto inizialmente stimato</td><td>Da valutare — informazioni preliminari</td></tr>
  </table>
</div>
"""
    elif notification_type == "formal_notification":
        extra_sections = f"""
<div class="section">
  <h2>Dettaglio Tecnico dell'Incidente</h2>
  <table>
    <tr><td>Descrizione</td><td>{_e(incident.description[:300])}</td></tr>
    <tr><td>Asset coinvolti</td><td>{_e(assets_preview)}</td></tr>
    <tr><td>Vettore di attacco</td><td>{_e(incident.incident_subcategory or 'Da specificare')}</td></tr>
  </table>
</div>
<div class="section">
  <h2>Misure Adottate</h2>
  <div class="fill-box">
    [COMPLETARE: misure di contenimento adottate]<br>
    [COMPLETARE: stato attuale del ripristino]<br>
    [COMPLETARE: misure preventive per evitare recidiva]
  </div>
</div>
"""
    elif notification_type == "final_report":
        rca = getattr(incident, "rca", None)
        rca_content = (
            f"<p>{_e(rca.summary)}</p>"
            if rca and rca.approved_at
            else "<p class='warning'>RCA non ancora approvato. Completare prima di inviare il Report Finale.</p>"
        )
        extra_sections = f"""
<div class="section">
  <h2>Analisi Causa Radice (RCA)</h2>
  {rca_content}
</div>
<div class="section">
  <h2>Misure di Rimedio Adottate</h2>
  <div class="fill-box">[COMPLETARE: descrizione completa delle misure adottate]</div>
</div>
<div class="section">
  <h2>Misure Preventive Future</h2>
  <div class="fill-box">[COMPLETARE: azioni preventive pianificate]</div>
</div>
<div class="section">
  <h2>Lezioni Apprese</h2>
  <div class="fill-box">[COMPLETARE: lesson learned principali]</div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>{_e(doc_title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 11px; color: #1f2937; margin: 24px; }}
    h1 {{ font-size: 16px; color: #dc2626; border-bottom: 3px solid #dc2626; padding-bottom: 8px; }}
    h2 {{ font-size: 12px; color: #1e40af; margin-top: 18px; border-left: 4px solid #1e40af; padding-left: 8px; }}
    .section {{ margin: 16px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
    th {{ background: #1e40af; color: white; padding: 6px 8px; text-align: left; font-size: 10px; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
    td:first-child {{ font-weight: bold; width: 35%; background: #f8fafc; }}
    .header-box {{ background: #fef2f2; border: 2px solid #dc2626; padding: 12px; border-radius: 6px; margin-bottom: 16px; }}
    .csirt-box {{ background: #eff6ff; border: 1px solid #93c5fd; padding: 12px; border-radius: 6px; margin: 12px 0; }}
    .fill-box {{ background: #fffbeb; border: 1px dashed #f59e0b; padding: 12px; margin: 8px 0; border-radius: 4px; color: #92400e; font-style: italic; }}
    .note {{ background: #f0f9ff; border-left: 3px solid #0ea5e9; padding: 8px; margin: 8px 0; font-size: 10px; }}
    .warning {{ color: #dc2626; font-weight: bold; }}
    .sig-badge {{ display: inline-block; background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; }}
    .signature {{ border: 1px solid #d1d5db; padding: 16px; margin-top: 24px; border-radius: 4px; }}
  </style>
</head>
<body>
<div class="header-box">
  <h1>{_e(doc_title)}</h1>
  <p><strong>Generato il:</strong> {_e(now_str)} | <strong>Da:</strong> {_e(user.get_full_name() or user.email)} | <strong>Scadenza:</strong> {_e(deadline_str)}</p>
</div>
<div class="csirt-box">
  <strong>Destinatario: {_e(csirt.get("name", "CSIRT Nazionale"))}</strong><br>
  Portale: <a href="{_e(csirt.get("portal", ""))}">{_e(csirt.get("portal", "—"))}</a><br>
  Email: {_e(csirt.get("email", "—"))}
</div>
<div class="section">
  <h2>1. Entita Notificante</h2>
  <table>
    <tr><td>Ragione sociale</td><td>{_e(legal_name)}</td></tr>
    <tr><td>Partita IVA / VAT</td><td>{_e(legal_vat)}</td></tr>
    <tr><td>Sito / Stabilimento</td><td>{_e(plant.name) if plant else "—"} ({_e(plant.code) if plant else "—"})</td></tr>
    <tr><td>Paese</td><td>{_e(plant.get_country_display()) if plant else "—"}</td></tr>
    <tr><td>Classificazione NIS2</td><td><span class="sig-badge">{_e(entity_type.upper())}</span></td></tr>
    <tr><td>Settore NIS2</td><td>{_e(sector)}</td></tr>
    <tr><td>Referente NIS2</td><td>{_e(contact_name)} — {_e(contact_email)}{_e(" — " + contact_phone) if contact_phone else ""}</td></tr>
  </table>
</div>
<div class="section">
  <h2>2. Identificazione Incidente</h2>
  <table>
    <tr><td>ID Interno</td><td><strong>{_e(str(incident.pk)[:8].upper())}</strong></td></tr>
    <tr><td>Riferimento CSIRT</td><td>{_e(incident.nis2_incident_ref or "[DA COMPILARE dopo ricezione dal CSIRT]")}</td></tr>
    <tr><td>Titolo</td><td>{_e(incident.title)}</td></tr>
    <tr><td>Data/ora rilevamento</td><td>{_e(detected)}</td></tr>
    <tr><td>Categoria ENISA</td><td>{_e(cat_label)}</td></tr>
    <tr><td>Severita</td><td>{_e(incident.severity.upper())}</td></tr>
    <tr><td>Classificazione</td><td><span class="sig-badge">SIGNIFICATIVO</span></td></tr>
  </table>
</div>
<div class="section">
  <h2>3. Impatto</h2>
  <table>{impact_rows}</table>
</div>
{extra_sections}
<div class="section">
  <h2>Timeline Notifiche</h2>
  <table>
    <tr><th>Tipo</th><th>Scadenza</th><th>Stato</th></tr>
    {("<tr><td>Early Warning (T+24h)</td><td>" + _e(incident.early_warning_deadline.strftime("%d/%m/%Y %H:%M") if incident.early_warning_deadline else "N/A - Entita Importante") + "</td><td>—</td></tr>") if entity_type == "essenziale" else ""}
    <tr><td>Notifica Formale (T+72h)</td><td>{_e(incident.formal_notification_deadline.strftime("%d/%m/%Y %H:%M") if incident.formal_notification_deadline else "—")}</td><td>—</td></tr>
    <tr><td>Report Finale (T+1 mese)</td><td>{_e(incident.final_report_deadline or "—")}</td><td>—</td></tr>
  </table>
</div>
<div class="signature">
  <strong>Dichiarazione</strong><br><br>
  Nome e cognome: _________________________<br>
  Qualifica: _________________________<br>
  Data: __________________ Firma: _________________________
</div>
</body>
</html>"""


def mark_notification_sent(
    incident: Incident,
    notification_type: str,
    user,
    protocol_ref: str = "",
    authority_response: str = "",
) -> NIS2Notification:
    """Registra notifica NIS2 inviata al CSIRT."""
    from core.audit import log_action

    csirt = get_csirt_for_plant(incident.plant)
    notif, _ = NIS2Notification.objects.update_or_create(
        incident=incident,
        notification_type=notification_type,
        defaults={
            "csirt_name": csirt.get("name", "—"),
            "csirt_portal": csirt.get("portal", ""),
            "csirt_country": incident.plant.country if incident.plant else "—",
            "sent_at": timezone.now(),
            "sent_by": user,
            "protocol_ref": protocol_ref,
            "authority_response": authority_response,
        },
    )

    log_action(
        user=user,
        action_code=f"incident.nis2.{notification_type}.sent",
        level="L1",
        entity=incident,
        payload={
            "notification_type": notification_type,
            "csirt": csirt.get("name", "—"),
            "protocol_ref": protocol_ref,
        },
    )
    return notif


def update_pdca_with_nis2_evidence(incident: Incident, notification: NIS2Notification):
    """Collega report finale NIS2 come evidenza al PDCA incidente."""
    if notification.notification_type != "final_report":
        return

    from apps.pdca.models import PdcaCycle

    pdca = PdcaCycle.objects.filter(
        trigger_type="incidente",
        trigger_source_id=incident.pk,
        deleted_at__isnull=True,
    ).first()
    if not pdca:
        return

    if pdca.fase_corrente == "do":
        from apps.documents.models import Evidence
        from apps.pdca.services import advance_phase

        ev = Evidence.objects.create(
            title=f"Report Finale NIS2 — {incident.title}",
            evidence_type="report",
            plant=incident.plant,
            valid_until=timezone.now().date() + timezone.timedelta(days=365),
            uploaded_by=notification.sent_by or incident.created_by,
            created_by=notification.sent_by or incident.created_by,
        )
        if notification.sent_by:
            try:
                advance_phase(
                    pdca,
                    notification.sent_by,
                    phase_notes=(
                        f"Report Finale NIS2 inviato al {notification.csirt_name}. "
                        f"Protocollo: {notification.protocol_ref or 'pendente'}"
                    ),
                    evidence=ev,
                )
            except Exception:
                pass
