"""Centro Operativo (M21) — logica di aggregazione e persistenza (regola #2).

Gli insight sono **calcolati al volo** dagli advisor (verità corrente). Qui:
- li filtriamo per scope plant, li **ordiniamo** e calcoliamo il **Posture Score**;
- li arricchiamo con lo **stato persistito** (`InsightState`) per snooze / rischio
  accettato / nota / owner, escludendo dalla lista principale quelli sospesi;
- riconciliamo lo stato (`sync_insights`, con auto-resolve) e storicizziamo la
  postura (`record_posture_snapshot`) per il trend.
"""
from __future__ import annotations

from django.utils import timezone

from apps.cockpit.insights import AREAS, AdvisorContext, collect_insights
from apps.cockpit.models import InsightState, InsightStatus, PostureSnapshot

SEVERITY_RANK = {"critical": 1000, "warning": 100, "info": 10}
AREA_WEIGHT = {"critical": 40, "warning": 15, "info": 5}


def _rank(insight) -> float:
    base = SEVERITY_RANK.get(insight.severity, 0)
    effort = insight.effort_h if insight.effort_h is not None else 1.0
    return base - min(effort, 20.0)


def _posture_from_dicts(insights: list[dict]) -> dict:
    areas = {a: {"critical": 0, "warning": 0, "info": 0} for a in AREAS}
    for i in insights:
        a = i["area"] if i["area"] in areas else "governance"
        if i["severity"] in areas[a]:
            areas[a][i["severity"]] += 1
    area_scores = {}
    for a, c in areas.items():
        score = min(100, AREA_WEIGHT["critical"] * c["critical"]
                    + AREA_WEIGHT["warning"] * c["warning"] + AREA_WEIGHT["info"] * c["info"])
        area_scores[a] = {"score": score, **c}
    total = round(sum(v["score"] for v in area_scores.values()) / len(AREAS))
    return {"total": total, "areas": area_scores}


def _counts(insights: list[dict]) -> dict:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for i in insights:
        if i["severity"] in counts:
            counts[i["severity"]] += 1
    counts["total"] = len(insights)
    return counts


def _user_roles(user):
    """Set dei codici ruolo dell'utente, o None se superuser (= vede tutto)."""
    if user is None:
        return set()
    if getattr(user, "is_superuser", False):
        return None
    from apps.auth_grc.models import UserPlantAccess
    return set(UserPlantAccess.objects.filter(user=user).values_list("role", flat=True))


def _enrich_and_split(insights, today):
    """Aggancia lo stato persistito a ogni insight; separa attivi da sospesi."""
    fps = [i.fingerprint for i in insights]
    states = {s.fingerprint: s for s in InsightState.objects.filter(fingerprint__in=fps)}
    active, suppressed = [], []
    for i in insights:
        d = i.to_dict()
        st = states.get(i.fingerprint)
        if st:
            d["state"] = {
                "status": st.status,
                "snoozed_until": st.snoozed_until.isoformat() if st.snoozed_until else None,
                "accepted_until": st.accepted_until.isoformat() if st.accepted_until else None,
                "note": st.note,
            }
            if st.is_suppressed(today):
                suppressed.append(d)
                continue
        else:
            d["state"] = None
        active.append(d)
    return active, suppressed


def build_cockpit(plant=None, user=None, include_suppressed=False, mine=False) -> dict:
    """`{insights (ranked, attivi), counts, posture, suppressed_count[, suppressed]}`.

    Gli insight sospesi (snooze/rischio-accettato ancora validi) sono esclusi dalla
    lista e dal Posture Score (accettare un rischio o rimandare migliora la vista —
    è una decisione esplicita). `mine` filtra agli insight di competenza dell'utente."""
    today = timezone.localdate()
    insights = collect_insights(AdvisorContext(plant=plant, user=user))
    if plant is not None:
        pid = str(plant.pk)
        insights = [i for i in insights if i.plant_id in (None, pid)]
    insights.sort(key=_rank, reverse=True)

    active, suppressed = _enrich_and_split(insights, today)

    if mine:
        roles = _user_roles(user)
        if roles is not None:
            active = [d for d in active if d["owner_role"] in roles]

    result = {
        "insights": active,
        "counts": _counts(active),
        "posture": _posture_from_dicts(active),
        "suppressed_count": len(suppressed),
    }
    if include_suppressed:
        result["suppressed"] = suppressed
    return result


# ---------------------------------------------------------------------------
# Persistenza: reconcile + snapshot + azioni
# ---------------------------------------------------------------------------

def sync_insights() -> dict:
    """Riconcilia `InsightState` con gli insight correnti (pattern `sync_findings`).

    Upsert per ogni insight presente; auto-resolve di quelli non più rilevati.
    Non tocca snooze/accettazione finché il problema persiste."""
    now = timezone.now()
    insights = collect_insights()
    existing = {s.fingerprint: s for s in InsightState.objects.all()}
    seen = set()
    created = updated = resolved = 0

    for i in insights:
        fp = i.fingerprint
        seen.add(fp)
        st = existing.get(fp)
        if st is None:
            InsightState.objects.create(
                fingerprint=fp, code=i.code, module=i.module, area=i.area,
                severity=i.severity, plant_id=i.plant_id or None,
                params_snapshot=i.params, owner_role=i.owner_role,
                status=InsightStatus.OPEN,
            )
            created += 1
        else:
            st.code, st.module, st.area, st.severity = i.code, i.module, i.area, i.severity
            st.plant_id = i.plant_id or None
            st.params_snapshot = i.params
            if i.owner_role:
                st.owner_role = i.owner_role
            if st.status == InsightStatus.RESOLVED:  # ricomparso → riapri
                st.status = InsightStatus.OPEN
                st.resolved_at = None
            st.save()
            updated += 1

    for fp, st in existing.items():
        if fp in seen or st.status == InsightStatus.RESOLVED:
            continue
        st.status = InsightStatus.RESOLVED
        st.resolved_at = now
        st.save(update_fields=["status", "resolved_at", "updated_at"])
        resolved += 1

    return {"created": created, "updated": updated, "resolved": resolved}


def record_posture_snapshot() -> int:
    """Salva lo snapshot odierno della postura: org + per ogni plant attivo.

    Colleziona gli insight una sola volta e ricalcola la postura per scope (evita
    di ri-eseguire gli advisor per ogni plant)."""
    from apps.plants.models import Plant

    today = timezone.localdate()
    all_insights = [i.to_dict() for i in collect_insights()]

    def _snap(plant_id, subset):
        PostureSnapshot.objects.update_or_create(
            plant_id=plant_id, taken_on=today,
            defaults={"total": _posture_from_dicts(subset)["total"],
                      "areas": _posture_from_dicts(subset)["areas"],
                      "counts": _counts(subset)},
        )

    _snap(None, all_insights)
    n = 1
    for plant in Plant.objects.filter(deleted_at__isnull=True):
        pid = str(plant.pk)
        subset = [d for d in all_insights if d["plant_id"] in (None, pid)]
        _snap(plant.id, subset)
        n += 1
    return n


def apply_insight_action(fingerprint: str, action: str, until=None, note: str = "", user=None):
    """Applica snooze/accept/reopen a un insight (per fingerprint). Ritorna lo
    `InsightState` aggiornato o None se il fingerprint non esiste (404)."""
    live = next((i for i in collect_insights() if i.fingerprint == fingerprint), None)
    existing = InsightState.objects.filter(fingerprint=fingerprint).first()
    if live is None and existing is None:
        return None

    defaults = {}
    if live is not None:
        defaults = {
            "code": live.code, "module": live.module, "area": live.area,
            "severity": live.severity, "plant_id": live.plant_id or None,
            "params_snapshot": live.params, "owner_role": live.owner_role,
        }
    st, _ = InsightState.objects.update_or_create(fingerprint=fingerprint, defaults=defaults)

    if action == "snooze":
        st.status, st.snoozed_until, st.accepted_until = InsightStatus.SNOOZED, until, None
    elif action == "accept":
        st.status, st.accepted_until, st.snoozed_until = InsightStatus.ACCEPTED_RISK, until, None
    elif action == "reopen":
        st.status, st.snoozed_until, st.accepted_until = InsightStatus.OPEN, None, None
    if note:
        st.note = note
    st.save()
    return st


# ---------------------------------------------------------------------------
# Step 3 — assistenza AI (L2, human-in-the-loop). Output SOLO proposto, mai
# applicato. Sanitize attivo (regola #9): nessun PII al cloud in chiaro.
# ---------------------------------------------------------------------------

_EXPLAIN_SYSTEM = (
    "Sei un assistente GRC per un'azienda manifatturiera automotive (TISAX, NIS2, ISO 27001). "
    "Spiega in modo chiaro il problema indicato e proponi una remediation concreta, attuabile e "
    "prioritizzata. Usa SOLO le informazioni del contesto: non inventare dati, nomi o numeri. "
    "Rispondi in italiano, in modo conciso."
)
_ASSISTANT_SYSTEM = (
    "Sei l'assistente del Centro Operativo GRC. Rispondi alla domanda basandoti ESCLUSIVAMENTE sul "
    "contesto fornito (i problemi aperti realmente rilevati). Cita i codici/controlli normativi "
    "pertinenti. Se la risposta non è ricavabile dal contesto, dillo esplicitamente. Non inventare. "
    "Rispondi in italiano, in modo conciso."
)


def _insight_by_fingerprint(fingerprint):
    return next((i for i in collect_insights() if i.fingerprint == fingerprint), None)


def ai_explain_insight(fingerprint: str, user=None):
    """Spiegazione + bozza di remediation per un insight (M20). Ritorna None se il
    fingerprint non esiste. Propaga `LlmUnavailable`/`ValueError` (gestiti dalla view).
    L'output è solo proposto: nessun apply automatico (human-in-the-loop)."""
    from apps.ai_engine.router import route

    ins = _insight_by_fingerprint(fingerprint)
    if ins is None:
        return None
    refs = "; ".join(f"{c.get('framework', '')} {c.get('control', '')}".strip() for c in ins.compliance_refs)
    prompt = (
        f"Problema rilevato — codice: {ins.code}; area: {ins.area}; gravità: {ins.severity}.\n"
        f"Dati: {ins.params}\n"
        f"Riferimenti normativi: {refs or 'n/d'}\n\n"
        "Fornisci: 1) perché è rilevante e che impatto ha; 2) una remediation in passi concreti; "
        "3) la priorità suggerita. Massimo ~200 parole."
    )
    result = route(
        task_type="cockpit_explain", prompt=prompt, system=_EXPLAIN_SYSTEM, user=user,
        entity_id=fingerprint, module_source="M21", sanitize=True,
        plant_ids=[ins.plant_id] if ins.plant_id else [], max_tokens=700,
    )
    return {"text": result.get("text", ""), "provider": result.get("provider", ""),
            "used_fallback": result.get("used_fallback", False)}


def ai_assistant(question: str, plant=None, user=None) -> dict:
    """Assistente 'Chiedi al Copilot': risponde **grounded** sugli insight correnti
    (no allucinazione). Propaga `LlmUnavailable`/`ValueError`."""
    from apps.ai_engine.router import route

    data = build_cockpit(plant=plant, user=user)
    plant_ids = set()
    lines = []
    for i in data["insights"][:30]:
        refs = ", ".join(f"{c['framework']} {c['control']}" for c in i["compliance_refs"])
        lines.append(f"- [{i['severity']}/{i['area']}] {i['code']} dati={i['params']} norme=({refs})")
        if i["plant_id"]:
            plant_ids.add(i["plant_id"])
    context = "\n".join(lines) or "(nessun problema aperto al momento)"
    prompt = (
        f"Domanda dell'utente: {question}\n\n"
        f"Contesto — problemi aperti rilevati ora dal Centro Operativo "
        f"(Posture Score {data['posture']['total']}/100, {data['counts']['total']} insight):\n{context}\n\n"
        "Rispondi alla domanda basandoti solo su questo contesto."
    )
    result = route(
        task_type="cockpit_assistant", prompt=prompt, system=_ASSISTANT_SYSTEM, user=user,
        entity_id="cockpit-assistant", module_source="M21", sanitize=True,
        plant_ids=list(plant_ids), max_tokens=900,
    )
    return {"text": result.get("text", "")}
