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


def explain_control(control, lang: str, user) -> dict:
    """
    Genera una spiegazione plain-language di cosa deve fare concretamente l'azienda
    per soddisfare il controllo. Il risultato viene salvato in
    control.translations[lang]['practical_summary'] per evitare chiamate ripetute.
    """
    title = control.get_title(lang)
    tr = control.translations.get(lang, control.translations.get("it", control.translations.get("en", {})))
    description = tr.get("description", "")[:600]
    guidance = tr.get("guidance", "")[:600]
    req = control.evidence_requirement or {}

    docs = [d.get("description") or d.get("type", "") for d in req.get("documents", []) if d.get("mandatory")]
    evs  = [e.get("description") or e.get("type", "") for e in req.get("evidences",  []) if e.get("mandatory")]

    lang_label = {"it": "italiano", "en": "English", "fr": "français", "pl": "polski", "tr": "Türkçe"}.get(lang, lang)

    prompt = f"""Sei un consulente GRC che deve spiegare a un responsabile aziendale (non tecnico) cosa fare per soddisfare questo requisito normativo.

Framework: {control.framework.code}
Controllo: {control.external_id} — {title}
Descrizione normativa: {description or "n/d"}
Linee guida: {guidance or "n/d"}
Documenti obbligatori: {", ".join(docs) if docs else "non specificati"}
Evidenze obbligatorie: {", ".join(evs) if evs else "non specificate"}

Scrivi un paragrafo di 3-5 frasi in {lang_label} che spieghi in modo semplice:
- Cosa deve produrre o fare concretamente l'azienda
- Che tipo di documento, policy o procedura è richiesta (se applicabile)
- Come si dimostra di essere in regola (evidenze tipiche)

Rispondi SOLO con JSON valido: {{"summary": "..."}}"""

    result = route(
        task_type="control_explain",
        prompt=prompt,
        system="Sei un consulente GRC. Rispondi solo con JSON valido, nessun testo aggiuntivo.",
        user=user,
        entity_id=control.pk,
        module_source="M03",
        sanitize=False,  # dati normativi pubblici, nessun PII
    )

    text = result.get("text", "")
    try:
        data = json.loads(text)
        summary = data.get("summary", "")
    except Exception:
        m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)\"', text, re.DOTALL)
        summary = m.group(1).replace("\\n", "\n").strip() if m else text.strip()

    if summary:
        translations = dict(control.translations or {})
        if lang not in translations:
            translations[lang] = {}
        else:
            translations[lang] = dict(translations[lang])
        translations[lang]["practical_summary"] = summary
        control.translations = translations
        control.save(update_fields=["translations", "updated_at"])

    return {
        "summary": summary,
        "interaction_id": str(result.get("interaction_id", "")),
        "provider": result.get("provider", ""),
        "model": result.get("model", ""),
    }


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
