"""
Motore di classificazione NIS2 — funzioni pure.
Nessun accesso al DB. Input: dict con valori incidente + config.
Output: dict strutturato con tutti i valori intermedi.

Unica fonte di verità per:
- classify_significance() (salvataggio)
- classification-breakdown (GET dopo salvataggio)
- classification-preview (POST in tempo reale)
- Test unitari
"""

# ── Tabella regole riservatezza ──────────────────────────────
# (categoria ENISA, dati personali) → punteggio
RISERVATEZZA_RULES = [
    (True, ["data_breach"], 5),
    (True, ["data_breach", "intrusion", "insider_threat"], 4),
    (True, [], 3),
    (False, ["data_breach"], 3),
    (False, ["intrusion", "intrusion_attempt", "insider_threat"], 2),
]
# default se nessuna regola corrisponde → 1

# ── Categorie ENISA per IS-2 e IS-4 ────────────────────────
IS2_CATEGORIES = {"data_breach", "intrusion", "insider_threat"}
IS4_CATEGORIES = {
    "intrusion",
    "intrusion_attempt",
    "insider_threat",
    "malicious_code",
}


def _score_threshold_axis(value, threshold, mul_medium: float, mul_high: float) -> int:
    """
    Converte un valore numerico in punteggio 1-5
    usando soglia base e due moltiplicatori.

    Scala:
      0 o None          → 1
      0 < v < soglia    → 2
      soglia ≤ v < ×mul_medium → 3
      ×mul_medium ≤ v < ×mul_high  → 4
      v ≥ ×mul_high     → 5
    """
    if not value or float(value) <= 0:
        return 1
    v = float(value)
    t = float(threshold)
    if v < t:
        return 2
    if v < t * mul_medium:
        return 3
    if v < t * mul_high:
        return 4
    return 5


def _score_riservatezza(personal_data: bool, category: str) -> int:
    """Punteggio asse riservatezza (1-5)."""
    cat = category or ""
    for has_pd, categories, score in RISERVATEZZA_RULES:
        if has_pd != personal_data:
            continue
        if not categories:
            return score
        if cat in categories:
            return score
    return 1


def _score_reputazionale(cross_border: bool, critical_infra: bool, severity: str) -> int:
    """Punteggio asse reputazionale (1-5)."""
    if cross_border and critical_infra:
        return 5
    if cross_border or critical_infra:
        return 4
    if severity == "critica":
        return 3
    if severity == "alta":
        return 2
    return 1


def compute_axis_scores(incident_data: dict, config: dict) -> dict:
    """
    Calcola i punteggi per i 5 assi.

    incident_data: {
      service_disruption_hours, financial_impact_eur,
      affected_users_count, personal_data_involved,
      cross_border_impact, critical_infrastructure_impact,
      incident_category, severity
    }
    config: {
      threshold_hours, threshold_financial, threshold_users,
      multiplier_medium, multiplier_high
    }

    Restituisce dict con punteggio + nota per ogni asse.
    """
    mul_med = float(config.get("multiplier_medium", 2.0))
    mul_high = float(config.get("multiplier_high", 3.0))

    t_hours = float(config.get("threshold_hours", 4.0))
    t_eur = float(config.get("threshold_financial", 100_000))
    t_users = float(config.get("threshold_users", 100))

    ore = float(incident_data.get("service_disruption_hours") or 0)
    eur = float(incident_data.get("financial_impact_eur") or 0)
    utenti = float(incident_data.get("affected_users_count") or 0)
    pd = bool(incident_data.get("personal_data_involved", False))
    cb = bool(incident_data.get("cross_border_impact", False))
    ici = bool(incident_data.get("critical_infrastructure_impact", False))
    cat = incident_data.get("incident_category", "") or ""
    sev = incident_data.get("severity", "bassa") or "bassa"

    s_op = _score_threshold_axis(ore, t_hours, mul_med, mul_high)
    s_eco = _score_threshold_axis(eur, t_eur, mul_med, mul_high)
    s_per = _score_threshold_axis(utenti, t_users, mul_med, mul_high)
    s_ris = _score_riservatezza(pd, cat)
    s_rep = _score_reputazionale(cb, ici, sev)

    return {
        "operativo": {
            "score": s_op,
            "value": ore,
            "threshold": t_hours,
            "note": (
                f"{ore}h fermo (soglia {t_hours}h, "
                f"×{mul_med}={t_hours * mul_med}h, "
                f"×{mul_high}={t_hours * mul_high}h)"
            ),
        },
        "economico": {
            "score": s_eco,
            "value": eur,
            "threshold": t_eur,
            "note": (
                f"€{eur:,.0f} (soglia €{t_eur:,.0f}, "
                f"×{mul_med}=€{t_eur * mul_med:,.0f}, "
                f"×{mul_high}=€{t_eur * mul_high:,.0f})"
            ),
        },
        "persone": {
            "score": s_per,
            "value": utenti,
            "threshold": t_users,
            "note": (
                f"{utenti:.0f} utenti (soglia {t_users:.0f}, "
                f"×{mul_med}={t_users * mul_med:.0f}, "
                f"×{mul_high}={t_users * mul_high:.0f})"
            ),
        },
        "riservatezza": {
            "score": s_ris,
            "value": None,
            "threshold": None,
            "note": f"Dati personali: {'sì' if pd else 'no'}, categoria: {cat or '—'}",
        },
        "reputazionale": {
            "score": s_rep,
            "value": None,
            "threshold": None,
            "note": (
                f"Cross-border: {'sì' if cb else 'no'}, "
                f"ICI: {'sì' if ici else 'no'}, "
                f"severity: {sev}"
            ),
        },
    }


def compute_pta_ptnr(scores: dict, is_recurrent: bool, recurrence_bonus: int = 2) -> dict:
    """
    Calcola PTA e PTNR dai punteggi degli assi.

    PTA  = max(5 assi)
    PTNR = PTA + bonus ricorrenza (0 o recurrence_bonus)
    """
    score_values = [v["score"] for v in scores.values()]
    pta = max(score_values)
    bonus = recurrence_bonus if is_recurrent else 0
    ptnr = pta + bonus

    return {
        "PTA": pta,
        "ricorrenza_bonus": bonus,
        "is_recurrent": is_recurrent,
        "PTNR": ptnr,
        "asse_dominante": max(scores, key=lambda k: scores[k]["score"]),
    }


def compute_fattispecie_acn(scores: dict, incident_data: dict, nis2_scope: str) -> dict:
    """
    Determina le fattispecie ACN attive.

    IS-1 → perdita riservatezza (score_riservatezza ≥ 3)
    IS-2 → integrità dati (dati personali + categoria sensibile)
    IS-3 → violazione SLA (score_operativo ≥ 3)
    IS-4 → accesso non autorizzato (solo essenziali)

    nis2_scope: "essenziale" | "importante" | "non_soggetto"
    """
    pd = bool(incident_data.get("personal_data_involved", False))
    cat = incident_data.get("incident_category", "") or ""

    is1 = scores["riservatezza"]["score"] >= 3
    is2 = pd and cat in IS2_CATEGORIES
    is3 = scores["operativo"]["score"] >= 3
    is4 = cat in IS4_CATEGORIES and nis2_scope == "essenziale"

    result = {
        "IS-1": {
            "active": is1,
            "label": "Perdita di riservatezza su dati digitali",
            "applicable": nis2_scope in ("essenziale", "importante"),
            "description": (
                f"Score riservatezza: "
                f"{scores['riservatezza']['score']}/5 "
                f"{'≥3 → attiva' if is1 else '<3 → inattiva'}"
            ),
        },
        "IS-2": {
            "active": is2,
            "label": "Perdita di integrità su dati digitali",
            "applicable": nis2_scope in ("essenziale", "importante"),
            "description": (
                f"Dati personali: {'sì' if pd else 'no'}, "
                f"categoria: {cat or '—'} "
                f"{'→ attiva' if is2 else '→ inattiva'}"
            ),
        },
        "IS-3": {
            "active": is3,
            "label": "Violazione SLA — interruzione servizio",
            "applicable": nis2_scope in ("essenziale", "importante"),
            "description": (
                f"Score operativo: "
                f"{scores['operativo']['score']}/5 "
                f"{'≥3 → attiva' if is3 else '<3 → inattiva'}"
            ),
        },
        "IS-4": {
            "active": is4,
            "label": "Accesso non autorizzato (solo essenziali)",
            "applicable": nis2_scope == "essenziale",
            "description": (
                f"Categoria: {cat or '—'}, "
                f"scope: {nis2_scope} "
                f"{'→ attiva' if is4 else '→ inattiva'}"
            ),
        },
    }

    return result


def compute_decision(
    ptnr_result: dict,
    fattispecie: dict,
    ptnr_threshold: int = 4,
    nis2_scope: str = "importante",
) -> dict:
    """
    Decisione finale: significativo o no.

    Regola: (PTNR >= soglia) OR (almeno una fattispecie attiva
            e applicabile)
    """
    ptnr = ptnr_result["PTNR"]

    active_applicable = [k for k, v in fattispecie.items() if v["active"] and v["applicable"]]

    by_ptnr = ptnr >= ptnr_threshold
    by_fattispecie = len(active_applicable) > 0
    is_significant = by_ptnr or by_fattispecie

    if nis2_scope == "non_soggetto":
        is_significant = False
        rationale = "Sito non soggetto a NIS2."
    elif is_significant:
        parts = []
        if by_ptnr:
            parts.append(f"PTNR={ptnr} ≥ soglia {ptnr_threshold}")
        if by_fattispecie:
            parts.append(f"fattispecie attive: {', '.join(active_applicable)}")
        rationale = "Significativo: " + " + ".join(parts) + "."
    else:
        rationale = (
            f"Non significativo: PTNR={ptnr} < {ptnr_threshold} "
            f"e nessuna fattispecie ACN attiva."
        )

    return {
        "is_significant": is_significant,
        "requires_csirt_notification": is_significant,
        "nis2_notifiable": "si" if is_significant else "no",
        "by_ptnr": by_ptnr,
        "by_fattispecie": by_fattispecie,
        "active_fattispecie": active_applicable,
        "rationale": rationale,
    }


def run_full_classification(
    incident_data: dict,
    config: dict,
    nis2_scope: str,
    is_recurrent: bool = False,
) -> dict:
    """
    Entry point principale — esegue i 4 step in sequenza.
    Restituisce il breakdown completo.

    Usato da:
    - classify_significance() per il salvataggio
    - GET breakdown per la UI
    - POST preview per il tempo reale
    - Test unitari
    """
    scores = compute_axis_scores(incident_data, config)
    pta_ptnr = compute_pta_ptnr(
        scores,
        is_recurrent,
        int(config.get("recurrence_score_bonus", 2)),
    )
    fattispecie = compute_fattispecie_acn(scores, incident_data, nis2_scope)
    decision = compute_decision(
        pta_ptnr,
        fattispecie,
        int(config.get("ptnr_threshold", 4)),
        nis2_scope,
    )

    return {
        "scores": scores,
        "pta_ptnr": pta_ptnr,
        "fattispecie": fattispecie,
        "decision": decision,
        "config_used": {
            "threshold_hours": config.get("threshold_hours"),
            "threshold_financial": config.get("threshold_financial"),
            "threshold_users": config.get("threshold_users"),
            "multiplier_medium": config.get("multiplier_medium"),
            "multiplier_high": config.get("multiplier_high"),
            "ptnr_threshold": config.get("ptnr_threshold"),
            "recurrence_bonus": config.get("recurrence_score_bonus"),
            "recurrence_window_days": config.get("recurrence_window_days"),
            "nis2_scope": nis2_scope,
        },
    }
