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
    # Fallback per campo: una lingua con il solo `practical_summary` già
    # generato non deve lasciare il prompt senza descrizione e linee guida.
    description = control.tr("description", lang)[:600]
    guidance = control.tr("guidance", lang)[:600]
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


_LANG_LABELS = {"it": "Italian", "en": "English", "fr": "French", "pl": "Polish", "tr": "Turkish"}


def _parse_json_object(text: str) -> dict:
    try:
        data = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        try:
            data = json.loads(match.group()) if match else {}
        except Exception:
            data = {}
    return data if isinstance(data, dict) else {}


# Controlli con molti requisiti (fino a 15 per un VH) e modelli che "ragionano"
# prima di rispondere (il ragionamento consuma lo stesso budget): con 3000
# token la risposta JSON veniva troncata.
_VDA_MAX_TOKENS = 8000

_VDA_MATURITY = (
    "VDA ISA maturity levels: 0 Incomplete (not implemented), 1 Performed (done informally), "
    "2 Managed (planned and tracked), 3 Established (defined, documented, applied), "
    "4 Predictable (measured and monitored), 5 Optimizing (continuously improved)."
)


def _requirements_block(requirements: list[dict]) -> str:
    return "\n".join(f'- [{r["id"]}] ({r["level"]}) {r["text"]}' for r in requirements)


def _conversation_block(topics: list[dict], followups: list[dict]) -> str:
    lines = []
    for t in topics:
        lines.append(f"Q: {t['question']}\nA: {t['answer'].strip() or '(no answer)'}")
    for f in followups:
        lines.append(f"Follow-up Q: {f['question']}\nA: {f['answer'].strip() or '(no answer)'}")
    return "\n\n".join(lines)


def _str_list(value, limit: int, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip()[:max_len] for x in value if isinstance(x, str) and x.strip()][:limit]


def generate_interview_topics(control, requirements: list[dict], lang: str, user) -> list[dict]:
    """Raggruppa i requisiti VDA ISA in 2-4 temi d'intervista nella lingua `lang`.

    Testo normativo pubblico: niente sanitize. L'esempio usa segnaposto tra
    parentesi quadre per ogni fatto specifico, così non può essere copiato come
    se fosse vero. Ogni requisito finisce in un tema: quelli che l'IA dimentica
    vanno nell'ultimo (la verifica dell'auditor controlla comunque tutti)."""
    lang_label = _LANG_LABELS.get(lang, lang)
    guidance = control.tr("guidance", "en")
    prompt = f"""VDA ISA control {control.external_id}: {control.get_title("en")}

Requirements (id, level, text):
{_requirements_block(requirements)}
{f"{chr(10)}Implementation guidance:{chr(10)}{guidance[:800]}{chr(10)}" if guidance else ""}
You are a TISAX auditor preparing the interview for this control. Group the requirements
into 2 to 4 topics, as you would ask them in a real audit interview (e.g. for a policy
control: the documents themselves; approval and review; communication to staff and partners).
Every requirement id must belong to exactly one topic; "should" requirements go into the
most related topic. Avoid topics that would make the site repeat the same answer.

For each topic, written in {lang_label}:
- "question": one open question (max 35 words) asking the site to explain how they do it
- "auditor_intent": what the auditor wants to understand (max 25 words)
- "what_to_mention": 3 to 6 short items the answer should cover (documents, roles,
  approval, frequency, tools, records)
- "example": an example answer of 2-3 sentences, in {lang_label}, where EVERY specific fact is a
  placeholder in square brackets written in {lang_label} (e.g. [document code], [role],
  [frequency], [tool], translated). Never invent concrete names, numbers or products.
- "req_ids": the requirement ids covered

Reply ONLY with valid JSON: {{"topics": [{{"question": "...", "auditor_intent": "...", "what_to_mention": ["..."], "example": "...", "req_ids": ["..."]}}]}}"""

    result = route(
        task_type="vda_interview",
        prompt=prompt,
        system="You are an experienced TISAX / VDA ISA auditor. Reply only with valid JSON.",
        user=user,
        entity_id=control.pk,
        module_source="M03",
        sanitize=False,  # dati normativi pubblici, nessun dato aziendale
        max_tokens=_VDA_MAX_TOKENS,
        timeout=120,
    )
    raw = _parse_json_object(result.get("text", "")).get("topics")
    if not isinstance(raw, list):
        return []
    valid_ids = [r["id"] for r in requirements]
    assigned: set[str] = set()
    topics = []
    for item in raw[:5]:
        if not isinstance(item, dict) or not str(item.get("question") or "").strip():
            continue
        req_ids = [x for x in (item.get("req_ids") or []) if x in valid_ids and x not in assigned]
        assigned.update(req_ids)
        topics.append({
            "id": f"t{len(topics) + 1}",
            "question": str(item["question"]).strip()[:400],
            "auditor_intent": str(item.get("auditor_intent") or "").strip()[:300],
            "what_to_mention": _str_list(item.get("what_to_mention"), 8, 150),
            "example": str(item.get("example") or "").strip()[:800],
            "req_ids": req_ids,
        })
    if topics:
        topics[-1]["req_ids"] += [x for x in valid_ids if x not in assigned]
    return topics


def review_vda_interview(instance, requirements: list[dict], topics: list[dict],
                         followups: list[dict], references: list[str], lang: str,
                         round_no: int, max_rounds: int, user) -> dict:
    """Verifica "da auditor" delle risposte: copertura per requisito, domande di
    approfondimento, evidenze da preparare, maturità sostenuta dalle risposte."""
    control = instance.control
    lang_label = _LANG_LABELS.get(lang, lang)
    refs = "\n".join(f"- {x}" for x in references) or "- none"
    last = round_no >= max_rounds
    prompt = f"""VDA ISA control {control.external_id}: {control.get_title("en")}

Requirements (id, level, text):
{_requirements_block(requirements)}

Interview with the site (answers in {lang_label}):
{_conversation_block(topics, followups)}

Documents and evidence already linked to this control:
{refs}

Maturity level currently declared: {instance.calc_maturity_level}
{_VDA_MATURITY}

You are the TISAX auditor. This is review round {round_no} of {max_rounds}.
1. "coverage": for EVERY requirement id, "covered" (an answer explicitly addresses it),
   "partial" or "missing". Judge only on what is written, never assume.
2. "followups": at most 3 questions in {lang_label} about the most important gaps
   ("must", "high", "very_high" first), specific and referring to what the site said.
   Never ask again something already answered. Empty list if nothing important is missing.
   {"This is the LAST round: ask only what is essential." if last else ""}
3. "evidence": up to 6 records or documents you would ask to see on site for this control,
   in {lang_label}; "linked" is the exact name from the linked list above if one matches,
   otherwise "".
4. "maturity": the highest level (0-5) the answers support, with one sentence in
   {lang_label} explaining why (and what is missing for the next level).
5. "summary": 1-2 sentences in {lang_label} with your overall impression.

Reply ONLY with valid JSON:
{{"coverage": {{"<id>": "covered"}}, "followups": [{{"question": "...", "req_ids": ["<id>"]}}], "evidence": [{{"item": "...", "linked": ""}}], "maturity": {{"supported_level": 3, "comment": "..."}}, "summary": "..."}}"""

    result = route(
        task_type="vda_interview",
        prompt=prompt,
        system=(
            "You are a strict but fair TISAX auditor. You assess only what the site states. "
            "Reply only with valid JSON."
        ),
        user=user,
        entity_id=instance.pk,
        module_source="M03",
        sanitize=True,
        plant_ids=[instance.plant_id] if instance.plant_id else [],
        max_tokens=_VDA_MAX_TOKENS,
        timeout=120,
    )
    data = _parse_json_object(result.get("text", ""))
    coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
    followups_out = []
    for f in data.get("followups") or []:
        if isinstance(f, dict) and str(f.get("question") or "").strip():
            followups_out.append({
                "question": str(f["question"]).strip()[:400],
                "req_ids": [str(x) for x in (f.get("req_ids") or []) if isinstance(x, str)],
            })
    evidence = []
    for e in data.get("evidence") or []:
        if isinstance(e, dict) and str(e.get("item") or "").strip():
            evidence.append({"item": str(e["item"]).strip()[:200], "linked": str(e.get("linked") or "").strip()})
    maturity = data.get("maturity") if isinstance(data.get("maturity"), dict) else {}
    try:
        level = min(5, max(0, int(maturity.get("supported_level"))))
    except (TypeError, ValueError):
        level = None
    return {
        "coverage": {str(k): str(v) for k, v in coverage.items()},
        "followups": followups_out,
        "evidence": evidence,
        "maturity": {"supported_level": level, "comment": str(maturity.get("comment") or "").strip()[:500]},
        "summary": str(data.get("summary") or "").strip()[:600],
        "interaction_id": result.get("interaction_id"),
    }


def draft_vda_implementation(instance, requirements: list[dict], topics: list[dict],
                             followups: list[dict], gaps: list[dict] | None,
                             references: list[str], lang: str, user) -> dict:
    """Bozza della "Implementation description" VDA ISA dall'intervista.

    Il testo va in audit TISAX: il prompt vieta di aggiungere fatti non presenti
    nelle risposte, impone un fatto una volta sola (le risposte ai temi e agli
    approfondimenti si sovrappongono) e il segnaposto `[TO BE COMPLETED: ...]`
    per i requisiti obbligatori scoperti. Le risposte passano dal Sanitizer."""
    control = instance.control
    lang_label = _LANG_LABELS.get(lang, lang)
    refs = "\n".join(f"- {x}" for x in references) or "- none"
    if gaps is None:
        gap_rule = ('For every "must", "high" or "very_high" requirement that no answer addresses, '
                    'add a line "[TO BE COMPLETED: <requirement in max 10 words>]".')
    elif gaps:
        gap_rule = ("The auditor review found these mandatory requirements NOT covered; add for each a line "
                    '"[TO BE COMPLETED: <requirement in max 10 words>]":\n'
                    + _requirements_block(gaps))
    else:
        gap_rule = "The auditor review found no uncovered mandatory requirement: add no placeholder."

    prompt = f"""VDA ISA control {control.external_id}: {control.get_title("en")}

Requirements (id, level, text):
{_requirements_block(requirements)}

Interview with the site (answers in {lang_label}):
{_conversation_block(topics, followups)}

Documents and evidence linked to this control:
{refs}

Write the "Implementation description" for the VDA ISA self-assessment.

Rules:
1. Use ONLY facts stated in the answers. Never add tools, products, frequencies, roles,
   documents or measures that are not in the answers. Never claim that a document covers,
   references or includes something unless an answer says so explicitly. If unsure, leave it out.
2. Describe only what the organization DOES. Do not mention the interview, the auditor, the
   requirements, missing evidence or what is not described; no summary or conclusion
   ("Overall ..."). Never write sentences like "No other ... are described" or
   "... is not mentioned". Requirements without an answer are simply left out (see rule 5).
3. English, factual, third person ("The organization ...", "The policy ..."). Present tense
   for current practice, past tense for dated events ("was approved in 2025").
4. Organize the text by topic in short paragraphs. State each fact ONCE: answers and
   follow-ups overlap, merge them and never repeat a sentence or a fact.
   Do not list the linked documents: they are exported in a separate "Reference
   documentation" column. Name a document only when an answer names it.
5. If an answer says something is NOT done or only partially, state it honestly in one sentence.
   {gap_rule}
6. Max 200 words.
7. "draft_local" is a faithful translation of "draft_en" into {lang_label}
   (keep the [TO BE COMPLETED] markers, translated).

Reply ONLY with valid JSON: {{"draft_en": "...", "draft_local": "..."}}"""

    result = route(
        task_type="vda_interview",
        prompt=prompt,
        system=(
            "You write VDA ISA (TISAX) self-assessment texts that an auditor will verify on site. "
            "Accuracy matters more than completeness. Reply only with valid JSON."
        ),
        user=user,
        entity_id=instance.pk,
        module_source="M03",
        sanitize=True,
        plant_ids=[instance.plant_id] if instance.plant_id else [],
        max_tokens=_VDA_MAX_TOKENS,
        timeout=120,
    )
    data = _parse_json_object(result.get("text", ""))
    return {
        "draft_en": str(data.get("draft_en") or "").strip(),
        "draft_local": str(data.get("draft_local") or "").strip(),
        "interaction_id": result.get("interaction_id"),
        "provider": result.get("provider", ""),
        "model": result.get("model", ""),
        "used_fallback": result.get("used_fallback", False),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risk assessment (M06): bozza della valutazione, misure, revisione delle
# motivazioni, sintesi per l'organo. Output sempre proposto, mai applicato:
# l'utente accetta campo per campo (regola 9). La classe resta della matrice.
# ─────────────────────────────────────────────────────────────────────────────

_LANG_NAMES = {"it": "italiano", "en": "English", "fr": "français", "pl": "polski", "tr": "Türkçe"}
_RISK_SYSTEM = (
    "Sei un risk manager esperto di sicurezza delle informazioni nel settore automotive (TISAX/VDA ISA, NIS2). "
    "Applichi la procedura aziendale di risk management: il rischio è la minaccia a un obiettivo aziendale; "
    "probabilità e impatto si scelgono SOLO con i criteri forniti; l'impatto è il caso peggiore fra le dimensioni. "
    "Non inventi fatti non presenti nei dati: se un dato manca fai una stima prudente e lo dici nella motivazione. "
    "Rispondi SOLO in JSON valido."
)


def _lang_name(lang: str) -> str:
    return _LANG_NAMES.get((lang or "it")[:2], "italiano")


# Regole comuni a bozza e identificazione. Senza la regola sugli impatti il
# modello, su un rischio con pochi dati, lasciava tutte le dimensioni a null.
_RISK_DRAFT_RULES = """- "probability_method": un solo valore, "frequenza" oppure "fer".
- Obiettivi aziendali: da 1 a 3 numeri dell'elenco, quelli che la minaccia mette davvero a rischio.
- Impatti: dai SEMPRE un livello 1–5 a ogni dimensione misurata dagli obiettivi scelti e a quelle colpite dalle
  proprietà C/I/A della minaccia; null solo per le dimensioni estranee allo scenario. Se mancano dati specifici,
  stima il caso peggiore plausibile per un sito manifatturiero automotive e scrivi nella motivazione che è una stima
  da verificare (es. quale dato manca). Usa le soglie economiche del registro.
- Classi di informazioni: i numeri delle classi colpite (per minacce a riservatezza o integrità quasi sempre almeno
  una; [] solo se nessuna è coinvolta). Processo BIA: il numero del più colpito, o null.
- Motiva probabilità e impatto citando il criterio del livello scelto, dimensione per dimensione, e i dati.
- Trattamento fra: mitigare, evitare, trasferire, accettare. Se non accetti indica il rischio atteso dopo le misure.
- Minaccia alla riservatezza (C): l'impatto, anche quello atteso, non scende sotto la classe di protezione delle
  informazioni colpite (very_high=5, high=4, normal=3, low=2); il trattamento può ridurre solo la probabilità."""

_RISK_DRAFT_FIELDS = """"vulnerability": "...", "consequence": "conseguenza sugli obiettivi aziendali",
 "probability_method": "fer", "probability": 3, "probability_rationale": "...",
 "impacts": {"economic": 3, "legal": null, "customer": 4, "reputational": 2, "people": null, "operational": 4},
 "impact_rationale": "...", "treatment": "mitigare", "treatment_rationale": "...",
 "expected_probability": 2, "expected_impact": 3, "objectives": [1], "information": [2], "process": 1"""


def _risk_plants(risk) -> list:
    return [risk.plant_id] if risk.plant_id else []


def draft_risk_assessment(risk, user, lang: str = "it") -> dict:
    """Bozza di valutazione di un rischio: vulnerabilità, conseguenza,
    probabilità, impatto per dimensione, trattamento, rischio atteso e
    riferimenti (obiettivi aziendali, classi di informazioni, processo BIA)."""
    from apps.risk.services import (
        PROCEDURE_CRITERIA, ai_link_candidates, ai_link_names, ai_link_payload, clamp_ai_expected_impact,
        economic_criteria, risk_ai_context, validate_ai_draft, validate_ai_links,
    )

    criteria = {**PROCEDURE_CRITERIA, "economic": economic_criteria(risk.plant)}
    links = ai_link_candidates(risk.plant)
    prompt = f"""Prepara una bozza di valutazione del rischio seguente.

DATI DEL RISCHIO (JSON):
{json.dumps(risk_ai_context(risk, lang), ensure_ascii=False, indent=1)}

ELENCHI DEL REGISTRO (scegli per numero "n"):
{json.dumps(ai_link_payload(links), ensure_ascii=False, indent=1)}

CRITERI DELLA PROCEDURA (livelli 1–5 per probabilità e per ogni dimensione d'impatto):
{json.dumps(criteria, ensure_ascii=False, indent=1)}

Regole:
{_RISK_DRAFT_RULES}
- Scrivi i testi in {_lang_name(lang)}, frasi brevi.

Rispondi con questo JSON (i valori sono solo un esempio di formato):
{{{_RISK_DRAFT_FIELDS}}}"""
    result = route(
        task_type="risk_draft", prompt=prompt, system=_RISK_SYSTEM, user=user, entity_id=risk.pk,
        module_source="M06", sanitize=True, plant_ids=_risk_plants(risk), max_tokens=4000,
    )
    data = _parse_json_object(result["text"])
    proposal = {**validate_ai_draft(data), **{k: v for k, v in validate_ai_links(data, links).items() if v}}
    # Soglia di riservatezza sulle classi proposte, altrimenti su quelle già collegate.
    info_ids = proposal.get("information_classes") or list(risk.information_classes.values_list("pk", flat=True))
    proposal = clamp_ai_expected_impact(proposal, risk.threat, info_ids)
    return {**result, "proposal": proposal, "names": ai_link_names(links)}


def identify_risks(plant, asset_type: str, threats: list, links: dict, user, entity_id,
                   lang: str = "it") -> dict:
    """Identificazione dai buchi di copertura: per ogni minaccia scoperta della
    tipologia, applicabile (con bozza della valutazione) o non applicabile."""
    from apps.risk.services import (
        PROCEDURE_CRITERIA, economic_criteria, risk_identification_context, validate_ai_identification,
    )

    criteria = {**PROCEDURE_CRITERIA, "economic": economic_criteria(plant)}
    catalog = [{"threat": t.code, "titolo": t.get_title(lang), "descrizione": t.tr("description", lang),
                "cia": t.cia} for t in threats]
    prompt = f"""Per il registro dei rischi seguente, decidi per OGNI minaccia elencata se si applica alla
tipologia di asset "{asset_type}" e, se si applica, prepara la bozza della valutazione.

CONTESTO DEL REGISTRO (JSON; processi, obiettivi e classi di informazioni si scelgono per numero "n"):
{json.dumps(risk_identification_context(plant, asset_type, links, lang), ensure_ascii=False, indent=1)}

MINACCE NON ANCORA VALUTATE:
{json.dumps(catalog, ensure_ascii=False, indent=1)}

CRITERI DELLA PROCEDURA (livelli 1–5 per probabilità e per ogni dimensione d'impatto):
{json.dumps(criteria, ensure_ascii=False, indent=1)}

Regole:
- "applicable": false SOLO se la minaccia non può realisticamente colpire questa tipologia nel registro
  (es. nessun asset o attività esposta); in "reason" il motivo verificabile dai dati. Nel dubbio è applicabile.
- Se applicabile: vulnerabilità e conseguenza concrete per il registro e la valutazione completa.
{_RISK_DRAFT_RULES}
- Scrivi i testi in {_lang_name(lang)}, frasi brevi.

Rispondi con questo JSON, una voce per minaccia (i valori sono solo un esempio di formato):
{{"items": [{{"threat": "codice", "applicable": true, "reason": "",
 {_RISK_DRAFT_FIELDS}}}]}}"""
    result = route(
        task_type="risk_identify", prompt=prompt, system=_RISK_SYSTEM, user=user, entity_id=entity_id,
        module_source="M06", sanitize=True, plant_ids=[plant.pk] if plant else [], max_tokens=8000,
        timeout=180,
    )
    items = _parse_json_object(result["text"]).get("items", [])
    return {**result, "items": validate_ai_identification(items, threats, links)}


def suggest_risk_measures(risk, user, lang: str = "it") -> dict:
    """Misure del piano di trattamento collegate ai controlli VDA ISA del sito."""
    from apps.risk.services import (
        ai_control_candidates, risk_ai_context, treatment_rule, validate_ai_measures,
    )

    candidates = ai_control_candidates(risk)
    controls = [
        {"n": i, "controllo": ci.control.external_id, "titolo": ci.control.get_title(lang), "stato": ci.status}
        for i, ci in enumerate(candidates, start=1)
    ]
    months = (treatment_rule(risk.current_class) or {}).get("months", 12)
    prompt = f"""Proponi da 3 a 5 misure concrete per trattare il rischio seguente (classe {risk.current_class},
trattamento {risk.treatment or "da definire"}), da completare entro {months} mesi.

DATI DEL RISCHIO (JSON):
{json.dumps(risk_ai_context(risk, lang), ensure_ascii=False, indent=1)}

CONTROLLI DEL SITO (collega ogni misura al controllo più pertinente, se c'è, indicandone il numero "n"):
{json.dumps(controls, ensure_ascii=False)}

Scrivi in {_lang_name(lang)}. Rispondi con questo JSON:
{{"measures": [{{"action": "misura concreta e verificabile", "expected_effect": "probabilita|impatto|entrambi",
  "weeks": 8, "control": 3, "rationale": "perché riduce il rischio"}}]}}"""
    result = route(
        task_type="risk_measures", prompt=prompt, system=_RISK_SYSTEM, user=user, entity_id=risk.pk,
        module_source="M06", sanitize=True, plant_ids=_risk_plants(risk), max_tokens=2500,
    )
    items = _parse_json_object(result["text"]).get("measures", [])
    return {**result, "measures": validate_ai_measures(items, risk, candidates)}


def review_risk_rationales(risks: list, user, entity_id, plant_ids: list, lang: str = "it") -> dict:
    """Revisione delle motivazioni: livelli scelti coerenti con i testi e i criteri."""
    from apps.risk.services import IMPACT_DIMENSIONS, PROCEDURE_CRITERIA, risk_label

    rows = []
    for i, r in enumerate(risks, start=1):
        rows.append({
            "n": i, "rischio": risk_label(r, lang), "minaccia": r.threat.code if r.threat else None,
            "probabilita": r.probability, "motivazione_probabilita": (r.probability_rationale or "")[:500],
            "impatti": {d: getattr(r, f"impact_{d}") for d in IMPACT_DIMENSIONS if getattr(r, f"impact_{d}")},
            "motivazione_impatto": (r.impact_rationale or "")[:500],
            "classe": r.current_class,
        })
    prompt = f"""Controlla la coerenza delle motivazioni di questi rischi con i livelli scelti e con i criteri.
Segnala SOLO i casi con un problema reale: motivazione generica, livello non giustificato dal testo,
testo che descrive un livello diverso da quello scelto. Non ripetere i dati.

CRITERI: {json.dumps(PROCEDURE_CRITERIA, ensure_ascii=False)}

RISCHI: {json.dumps(rows, ensure_ascii=False)}

Scrivi in {_lang_name(lang)}. Rispondi con questo JSON:
{{"findings": [{{"n": 1, "issue": "problema in una frase", "suggestion": "come correggere"}}]}}"""
    result = route(
        task_type="risk_review", prompt=prompt, system=_RISK_SYSTEM, user=user, entity_id=entity_id,
        module_source="M06", sanitize=True, plant_ids=plant_ids, max_tokens=3000,
    )
    findings = []
    for f in _parse_json_object(result["text"]).get("findings", [])[:30]:
        n = f.get("n") if isinstance(f, dict) else None
        if isinstance(n, int) and 1 <= n <= len(risks) and str(f.get("issue") or "").strip():
            risk = risks[n - 1]
            findings.append({
                "risk_id": str(risk.pk), "risk_name": risk_label(risk, lang),
                "issue": str(f["issue"]).strip()[:400], "suggestion": str(f.get("suggestion") or "").strip()[:400],
            })
    return {**result, "findings": findings}


def draft_risk_summary(digest: dict, user, entity_id, plant_ids: list, lang: str = "it") -> dict:
    """Bozza di relazione del registro per l'organo e il riesame di direzione."""
    prompt = f"""Scrivi una relazione sintetica (250–400 parole) sullo stato del risk assessment per l'organo di
amministrazione, a partire SOLO da questi dati:

{json.dumps(digest, ensure_ascii=False, indent=1)}

Struttura: 1) situazione generale e copertura; 2) obiettivi aziendali più esposti; 3) rischi High e Critical non
accettati e trattamento; 4) accettazioni e misure in ritardo; 5) decisioni richieste all'organo.
Tono formale, frasi brevi, nessun dato inventato. Scrivi in {_lang_name(lang)}.
Rispondi con questo JSON: {{"summary": "testo"}}"""
    result = route(
        task_type="risk_summary", prompt=prompt, system=_RISK_SYSTEM, user=user, entity_id=entity_id,
        module_source="M06", sanitize=True, plant_ids=plant_ids, max_tokens=2500,
    )
    summary = str(_parse_json_object(result["text"]).get("summary") or "").strip()
    return {**result, "summary": summary[:6000]}
