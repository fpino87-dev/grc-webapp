import html as html_module
from datetime import timedelta

from django.utils import timezone

from apps.plants.models import CSIRT_BY_COUNTRY

from .models import ENISA_INCIDENT_CATEGORIES, ENISA_SUBCATEGORIES, Incident, NIS2Configuration, NIS2Notification
from .nis2_classification import run_full_classification


def _e(value) -> str:
    """Escape HTML per prevenire XSS nel documento generato."""
    if value is None:
        return "—"
    return html_module.escape(str(value))


def _config_dict_from_obj(config_obj: NIS2Configuration | None) -> dict:
    return {
        "threshold_hours": float(config_obj.threshold_hours) if config_obj else 4.0,
        "threshold_financial": float(config_obj.threshold_financial) if config_obj else 100_000.0,
        "threshold_users": int(config_obj.threshold_users) if config_obj else 100,
        "multiplier_medium": float(config_obj.multiplier_medium) if config_obj else 2.0,
        "multiplier_high": float(config_obj.multiplier_high) if config_obj else 3.0,
        "ptnr_threshold": int(config_obj.ptnr_threshold) if config_obj else 4,
        "recurrence_score_bonus": int(config_obj.recurrence_score_bonus) if config_obj else 2,
        "recurrence_window_days": int(config_obj.recurrence_window_days) if config_obj else 90,
    }


def _incident_data_dict(incident: Incident) -> dict:
    return {
        "service_disruption_hours": incident.service_disruption_hours,
        "financial_impact_eur": incident.financial_impact_eur,
        "affected_users_count": incident.affected_users_count,
        "personal_data_involved": incident.personal_data_involved,
        "cross_border_impact": incident.cross_border_impact,
        "critical_infrastructure_impact": incident.critical_infrastructure_impact,
        "incident_category": incident.incident_category,
        "severity": incident.severity,
    }


def _recurrence_similar_queryset(incident: Incident, config: dict):
    if not incident.incident_category or not incident.plant_id:
        return Incident.objects.none()

    window = int(config.get("recurrence_window_days", 90))
    cutoff = timezone.now() - timedelta(days=window)

    return Incident.objects.filter(
        plant=incident.plant,
        incident_category=incident.incident_category,
        status="chiuso",
        detected_at__gte=cutoff,
        deleted_at__isnull=True,
    ).exclude(pk=incident.pk)


def _check_recurrence(incident: Incident, config: dict) -> bool:
    """
    Verifica automatica ricorrenza:
    esiste un incidente chiuso degli ultimi N giorni
    sullo stesso plant con la stessa categoria ENISA?
    """
    return _recurrence_similar_queryset(incident, config).exists()


def _last_similar_closed_at(incident: Incident, config: dict):
    qs = _recurrence_similar_queryset(incident, config).order_by("-closed_at", "-detected_at")
    prev = qs.first()
    return prev.closed_at or prev.detected_at if prev else None


def _apply_classification_result(incident: Incident, result: dict) -> None:
    scores = result["scores"]
    pta_ptnr = result["pta_ptnr"]
    decision = result["decision"]
    fatt = result["fattispecie"]
    active_codes = [k for k, v in fatt.items() if v["active"] and v["applicable"]]
    acn_str = ",".join(active_codes) if active_codes else ""

    incident.axis_operational = scores["operativo"]["score"]
    incident.axis_economic = scores["economico"]["score"]
    incident.axis_people = scores["persone"]["score"]
    incident.axis_confidentiality = scores["riservatezza"]["score"]
    incident.axis_reputational = scores["reputazionale"]["score"]
    incident.axis_recurrence = pta_ptnr["ricorrenza_bonus"]
    incident.pta_nis2 = pta_ptnr["PTA"]
    incident.ptnr_nis2 = pta_ptnr["PTNR"]
    incident.pt_gdpr = scores["riservatezza"]["score"] * (1 if incident.personal_data_involved else 0)
    incident.acn_is_category = acn_str or ""
    incident.requires_csirt_notification = bool(decision["requires_csirt_notification"])
    incident.requires_gdpr_notification = incident.pt_gdpr >= 4
    incident.is_significant = bool(decision["is_significant"])
    incident.nis2_notifiable = decision["nis2_notifiable"]


def classify_significance(incident: Incident) -> dict:
    """
    Thin wrapper: legge dal DB, chiama il motore puro,
    salva i risultati sul modello.
    Restituisce il breakdown completo.
    """
    plant = incident.plant
    nis2_scope = plant.nis2_scope if plant else "importante"

    config_obj = NIS2Configuration.objects.filter(plant=plant).first() if plant else None
    config = _config_dict_from_obj(config_obj)

    is_recurrent_auto = _check_recurrence(incident, config)
    is_recurrent_manual = bool(getattr(incident, "is_recurrent", False))
    is_recurrent = is_recurrent_auto or is_recurrent_manual

    incident_data = _incident_data_dict(incident)
    result = run_full_classification(incident_data, config, nis2_scope, is_recurrent)

    if incident.significance_override is not None:
        result["decision"]["is_significant"] = incident.significance_override
        result["decision"]["requires_csirt_notification"] = incident.significance_override
        result["decision"]["nis2_notifiable"] = "si" if incident.significance_override else "no"
        result["decision"]["rationale"] = (
            f"Override manuale: "
            f"{'significativo' if incident.significance_override else 'non significativo'}. "
            f"Motivazione: {incident.significance_override_reason or '—'}"
        )

    _apply_classification_result(incident, result)
    incident.save(
        update_fields=[
            "axis_operational",
            "axis_economic",
            "axis_people",
            "axis_confidentiality",
            "axis_reputational",
            "axis_recurrence",
            "pta_nis2",
            "ptnr_nis2",
            "pt_gdpr",
            "acn_is_category",
            "requires_csirt_notification",
            "requires_gdpr_notification",
            "is_significant",
            "nis2_notifiable",
            "updated_at",
        ]
    )

    if result["decision"]["is_significant"]:
        set_nis2_deadlines(incident)

    last_similar = _last_similar_closed_at(incident, config)
    result["recurrence"] = {
        "auto_detected": is_recurrent_auto,
        "manual_toggle": is_recurrent_manual,
        "bonus_applied": result["pta_ptnr"]["ricorrenza_bonus"],
        "last_similar_closed_at": last_similar.isoformat() if last_similar else None,
    }
    return result


def get_classification_breakdown(incident: Incident) -> dict:
    """Breakdown calcolato senza persistere (salvataggio solo in classify_significance)."""
    plant = incident.plant
    nis2_scope = plant.nis2_scope if plant else "importante"

    config_obj = NIS2Configuration.objects.filter(plant=plant).first() if plant else None
    config = _config_dict_from_obj(config_obj)

    is_recurrent_auto = _check_recurrence(incident, config)
    is_recurrent_manual = bool(getattr(incident, "is_recurrent", False))
    is_recurrent = is_recurrent_auto or is_recurrent_manual

    incident_data = _incident_data_dict(incident)
    result = run_full_classification(incident_data, config, nis2_scope, is_recurrent)

    if incident.significance_override is not None:
        result["decision"]["is_significant"] = incident.significance_override
        result["decision"]["requires_csirt_notification"] = incident.significance_override
        result["decision"]["nis2_notifiable"] = "si" if incident.significance_override else "no"
        result["decision"]["rationale"] = (
            f"Override manuale: "
            f"{'significativo' if incident.significance_override else 'non significativo'}. "
            f"Motivazione: {incident.significance_override_reason or '—'}"
        )

    last_similar = _last_similar_closed_at(incident, config)
    result["recurrence"] = {
        "auto_detected": is_recurrent_auto,
        "manual_toggle": is_recurrent_manual,
        "bonus_applied": result["pta_ptnr"]["ricorrenza_bonus"],
        "last_similar_closed_at": last_similar.isoformat() if last_similar else None,
    }
    return result


def get_classification_method(incident: Incident) -> dict:
    """Restituisce metodo esplicito di classificazione ENISA + NIS2."""
    config = NIS2Configuration.objects.filter(plant=incident.plant).first()
    threshold_users = int(config.threshold_users) if config else 100
    threshold_hours = float(config.threshold_hours) if config else 4.0
    threshold_financial = float(config.threshold_financial) if config else 100000.0
    multiplier_medium = float(config.multiplier_medium) if config else 2.0
    multiplier_high = float(config.multiplier_high) if config else 3.0
    ptnr_threshold = int(config.ptnr_threshold) if config else 4
    recurrence_window_days = int(config.recurrence_window_days) if config else 90

    categories = [
        {"code": code, "label": label, "description": description}
        for code, label, description in ENISA_INCIDENT_CATEGORIES
    ]
    subcategories = {
        key: [{"code": code, "label": label} for code, label in values]
        for key, values in ENISA_SUBCATEGORIES.items()
    }

    current_scores = {
        "axis_operational": incident.axis_operational,
        "axis_economic": incident.axis_economic,
        "axis_people": incident.axis_people,
        "axis_confidentiality": incident.axis_confidentiality,
        "axis_reputational": incident.axis_reputational,
        "axis_recurrence": incident.axis_recurrence,
        "pta_nis2": incident.pta_nis2,
        "ptnr_nis2": incident.ptnr_nis2,
        "pt_gdpr": incident.pt_gdpr,
        "acn_is_category": incident.acn_is_category or "",
        "requires_csirt_notification": incident.requires_csirt_notification,
        "requires_gdpr_notification": incident.requires_gdpr_notification,
    }

    return {
        "taxonomy": {
            "categories": categories,
            "subcategories": subcategories,
            "acn_is_categories": [
                {"code": "IS-1", "label": "Perdita di riservatezza verso esterno"},
                {"code": "IS-2", "label": "Perdita di integrita con impatto esterno"},
                {"code": "IS-3", "label": "Violazione SLA/livelli di servizio"},
                {"code": "IS-4", "label": "Accesso non autorizzato o abuso privilegi"},
            ],
        },
        "nis2_method": {
            "logic": "OR",
            "rule": (
                "PTA=max(5 assi); PTNR=PTA+bonus ricorrenza (se ricorrente). "
                "Significativo se PTNR≥soglia OPPURE almeno una fattispecie ACN attiva "
                "(IS-1…IS-4 in base a scope sito). Moltiplicatori M/H su soglie base per assi 1–3. "
                "Override manuale ha precedenza."
            ),
            "thresholds": {
                "affected_users_count": threshold_users,
                "service_disruption_hours": threshold_hours,
                "financial_impact_eur": threshold_financial,
                "multiplier_medium": multiplier_medium,
                "multiplier_high": multiplier_high,
                "ptnr_trigger_csirt": ptnr_threshold,
                "pt_gdpr_trigger": 4,
                "recurrence_window_days": recurrence_window_days,
            },
            "criteria": [
                {"key": "cross_border_impact", "label": "Impatto cross-border", "type": "boolean"},
                {"key": "critical_infrastructure_impact", "label": "Impatto su infrastrutture critiche", "type": "boolean"},
                {"key": "personal_data_involved", "label": "Coinvolgimento dati personali", "type": "boolean"},
                {
                    "key": "affected_users_count",
                    "label": "Utenti/sistemi coinvolti",
                    "type": "threshold",
                    "operator": ">=",
                    "threshold": threshold_users,
                },
                {
                    "key": "service_disruption_hours",
                    "label": "Ore di interruzione servizio",
                    "type": "threshold",
                    "operator": ">=",
                    "threshold": threshold_hours,
                },
                {
                    "key": "financial_impact_eur",
                    "label": "Impatto finanziario",
                    "type": "threshold",
                    "operator": ">=",
                    "threshold": threshold_financial,
                },
            ],
        },
        "scores": current_scores,
    }


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
            valid_until=timezone.now().date() + timedelta(days=365),
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
