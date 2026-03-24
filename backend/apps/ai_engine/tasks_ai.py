"""
Funzioni AI per i principali use case GRC.
"""

import json
import re

from .router import route


def classify_incident(incident, user) -> dict:
    from apps.incidents.models import ENISA_INCIDENT_CATEGORIES

    categories = "\n".join(f"- {c[0]}: {c[1]} ({c[2]})" for c in ENISA_INCIDENT_CATEGORIES)
    prompt = f"""Analizza questo incidente di sicurezza e classifica:

TITOLO: {incident.title}
DESCRIZIONE: {incident.description[:500]}

CATEGORIE ENISA disponibili:
{categories}

Rispondi SOLO con JSON valido, nessun testo aggiuntivo:
{{
  "category": "<codice_categoria>",
  "subcategory": "<sottocategoria o vuoto>",
  "severity": "<bassa|media|alta|critica>",
  "nis2_likely": <true|false>,
  "nis2_reason": "<motivo breve>",
  "confidence": <0.0-1.0>
}}"""

    result = route(
        task_type="incident_classify",
        prompt=prompt,
        system="Sei un esperto di cybersecurity e NIS2. Rispondi sempre e solo con JSON valido.",
        user=user,
        entity_id=incident.pk,
        module_source="M09",
        sanitize=True,
        plant_ids=[incident.plant_id] if incident.plant_id else [],
    )

    try:
        parsed = json.loads(result["text"])
    except Exception:
        match = re.search(r"\{.*\}", result["text"], re.DOTALL)
        parsed = json.loads(match.group()) if match else {}
    return {**result, "classification": parsed}


def suggest_gap_actions(control_instance, user) -> dict:
    control = control_instance.control
    framework = control.framework.code if control.framework else "ISO27001"
    prompt = f"""Un controllo di sicurezza è in stato GAP e richiede azioni correttive.

FRAMEWORK: {framework}
CONTROLLO: {control.external_id} — {control.get_title("it")}
STATO ATTUALE: {control_instance.status}
NOTE VALUTAZIONE: {control_instance.last_evaluated_note or "nessuna"}
SITO: {control_instance.plant.name if control_instance.plant else "—"}

Fornisci 3-5 azioni concrete e prioritizzate per raggiungere la conformità.
Rispondi SOLO con JSON valido:
{{
  "actions": [
    {{
      "priority": "alta",
      "title": "titolo azione",
      "description": "descrizione dettagliata",
      "estimated_weeks": 2,
      "owner_role": "compliance_officer",
      "evidence_needed": "tipo evidenza richiesta"
    }}
  ]
}}"""

    result = route(
        task_type="gap_actions",
        prompt=prompt,
        system=f"Sei un esperto di {framework} e sicurezza informatica industriale. Rispondi in JSON.",
        user=user,
        entity_id=control_instance.pk,
        module_source="M03",
        sanitize=True,
        plant_ids=[control_instance.plant_id] if control_instance.plant_id else [],
    )

    try:
        parsed = json.loads(result["text"])
    except Exception:
        match = re.search(r"\{.*\}", result["text"], re.DOTALL)
        parsed = json.loads(match.group()) if match else {}
    return {**result, "suggestions": parsed}


def draft_rca(incident, user) -> dict:
    assets_str = ", ".join(a.name for a in incident.assets.all()[:5]) or "non specificati"
    prompt = f"""Genera una bozza RCA per questo incidente:
- Titolo: {incident.title}
- Severità: {incident.severity}
- Asset coinvolti: {assets_str}
- Descrizione: {incident.description[:600]}

Rispondi SOLO con JSON valido:
{{
  "summary": "...",
  "root_cause": "...",
  "contributing_factors": ["..."],
  "timeline": ["..."],
  "immediate_actions": ["..."],
  "preventive_actions": ["..."],
  "lessons_learned": "..."
}}"""

    result = route(
        task_type="rca_draft",
        prompt=prompt,
        system="Sei un esperto di incident response e analisi forense. Rispondi solo in JSON valido.",
        user=user,
        entity_id=incident.pk,
        module_source="M09",
        sanitize=True,
        plant_ids=[incident.plant_id] if incident.plant_id else [],
    )

    try:
        parsed = json.loads(result["text"])
    except Exception:
        match = re.search(r"\{.*\}", result["text"], re.DOTALL)
        parsed = json.loads(match.group()) if match else {}
    return {**result, "rca_draft": parsed}
