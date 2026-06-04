"""Advisor OSINT per il Centro Operativo (M21).

Espone come `Insight` i problemi OSINT azionabili a livello di configurazione.
Step 0: salute delle chiavi enricher. Un provider con chiave **non valida**
(`enricher_health[provider].status == "invalid"`) è un problema concreto — gli
arricchimenti di quel provider girano a vuoto finché non si corregge la chiave.

`no_key` NON viene segnalato: una chiave non configurata (es. HIBP a pagamento)
è una scelta, non un guasto → evitarlo previene l'alert fatigue.
"""
from __future__ import annotations

from apps.cockpit.insights import Insight, register_advisor


@register_advisor
def enricher_key_health_advisor(context=None):
    from apps.osint.models import OsintSettings
    from apps.osint.health import KEYED_PROVIDERS

    settings = OsintSettings.load()
    health = settings.enricher_health or {}

    insights: list[Insight] = []
    for provider in KEYED_PROVIDERS:
        entry = health.get(provider) or {}
        if entry.get("status") != "invalid":
            continue
        insights.append(
            Insight(
                code="osint.key_invalid",
                module="osint",
                severity="warning",
                area="technical",
                action_type="navigate",
                plant_id=None,  # impostazione singleton, globale
                entity_ref={"type": "osint_settings", "id": provider, "deep_link": "/osint/settings"},
                params={"provider": provider, "detail": entry.get("detail", ""), "checked_at": entry.get("checked_at", "")},
                compliance_refs=[
                    {"framework": "NIS2", "control": "art.21 §2(e) — Sicurezza acquisizione/sviluppo"},
                ],
                effort_h=0.25,
                owner_role="ciso",
            )
        )
    return insights


@register_advisor
def critical_findings_advisor(context=None):
    """Finding OSINT critici aperti per plant (esposizione esterna attiva)."""
    from apps.osint.services import count_open_critical_findings_by_plant
    from apps.plants.models import Plant

    by_plant = count_open_critical_findings_by_plant()
    open_plants = {pid: n for pid, n in by_plant.items() if n > 0}
    if not open_plants:
        return []

    names = {
        str(pk): name
        for pk, name in Plant.objects.filter(pk__in=open_plants.keys()).values_list("pk", "name")
    }
    insights = []
    for plant_id, count in open_plants.items():
        plant_id = str(plant_id)
        insights.append(
            Insight(
                code="osint.critical_findings",
                module="osint",
                severity="critical",
                area="technical",
                action_type="navigate",
                plant_id=str(plant_id),
                entity_ref={"type": "plant", "id": str(plant_id), "deep_link": "/osint"},
                params={"count": count, "plant_name": names.get(plant_id, "")},
                compliance_refs=[{"framework": "NIS2", "control": "art.21 §2(a) — Gestione del rischio"}],
                effort_h=4.0,
                owner_role="ciso",
            )
        )
    return insights
