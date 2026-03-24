"""Test motore puro NIS2 (Determinazione ACN 379907/2025) — scenari da linee guida."""

from apps.incidents.nis2_classification import run_full_classification

CONFIG_IMPORTANTE = {
    "threshold_hours": 4.0,
    "threshold_financial": 100_000.0,
    "threshold_users": 100,
    "multiplier_medium": 2.0,
    "multiplier_high": 3.0,
    "ptnr_threshold": 4,
    "recurrence_score_bonus": 2,
    "recurrence_window_days": 90,
}


def test_scenario1_ransomware_lungo_importante():
    """Ransomware con fermo prolungato (Importante)."""
    incident_data = {
        "service_disruption_hours": 8,
        "financial_impact_eur": 50_000,
        "affected_users_count": 200,
        "personal_data_involved": False,
        "cross_border_impact": False,
        "critical_infrastructure_impact": False,
        "incident_category": "malicious_code",
        "severity": "critica",
    }
    r = run_full_classification(incident_data, CONFIG_IMPORTANTE, "importante", False)
    assert r["scores"]["operativo"]["score"] == 4
    assert r["scores"]["economico"]["score"] == 2
    assert r["scores"]["persone"]["score"] == 3
    assert r["scores"]["riservatezza"]["score"] == 1
    assert r["scores"]["reputazionale"]["score"] == 3
    assert r["pta_ptnr"]["PTA"] == 4
    assert r["pta_ptnr"]["PTNR"] == 4
    assert r["decision"]["is_significant"] is True
    assert "IS-3" in r["decision"]["active_fattispecie"]


def test_scenario2_data_breach_pd_importante():
    """Data breach con dati personali (Importante)."""
    incident_data = {
        "service_disruption_hours": 0,
        "financial_impact_eur": 0,
        "affected_users_count": 50,
        "personal_data_involved": True,
        "cross_border_impact": False,
        "critical_infrastructure_impact": False,
        "incident_category": "data_breach",
        "severity": "alta",
    }
    r = run_full_classification(incident_data, CONFIG_IMPORTANTE, "importante", False)
    assert r["scores"]["operativo"]["score"] == 1
    assert r["scores"]["economico"]["score"] == 1
    assert r["scores"]["persone"]["score"] == 2
    assert r["scores"]["riservatezza"]["score"] == 5
    assert r["scores"]["reputazionale"]["score"] == 2
    assert r["pta_ptnr"]["PTA"] == 5
    assert r["pta_ptnr"]["PTNR"] == 5
    assert r["decision"]["is_significant"] is True
    assert "IS-1" in r["decision"]["active_fattispecie"]
    assert "IS-2" in r["decision"]["active_fattispecie"]


def test_scenario3_minore_non_significativo():
    """Incidente minore non significativo (Importante)."""
    incident_data = {
        "service_disruption_hours": 1,
        "financial_impact_eur": 5_000,
        "affected_users_count": 10,
        "personal_data_involved": False,
        "cross_border_impact": False,
        "critical_infrastructure_impact": False,
        "incident_category": "other",
        "severity": "bassa",
    }
    r = run_full_classification(incident_data, CONFIG_IMPORTANTE, "importante", False)
    assert r["scores"]["operativo"]["score"] == 2
    assert r["scores"]["economico"]["score"] == 2
    assert r["scores"]["persone"]["score"] == 2
    assert r["scores"]["riservatezza"]["score"] == 1
    assert r["scores"]["reputazionale"]["score"] == 1
    assert r["pta_ptnr"]["PTA"] == 2
    assert r["pta_ptnr"]["PTNR"] == 2
    assert r["decision"]["is_significant"] is False


def test_scenario4_intrusion_essenziale_is4():
    """Accesso non autorizzato (Essenziale) — significativo per IS-4."""
    incident_data = {
        "service_disruption_hours": 0,
        "financial_impact_eur": 0,
        "affected_users_count": 0,
        "personal_data_involved": False,
        "cross_border_impact": False,
        "critical_infrastructure_impact": False,
        "incident_category": "intrusion",
        "severity": "media",
    }
    r = run_full_classification(incident_data, CONFIG_IMPORTANTE, "essenziale", False)
    assert r["scores"]["operativo"]["score"] == 1
    assert r["scores"]["economico"]["score"] == 1
    assert r["scores"]["persone"]["score"] == 1
    assert r["scores"]["riservatezza"]["score"] == 2
    assert r["scores"]["reputazionale"]["score"] == 1
    assert r["pta_ptnr"]["PTA"] == 2
    assert r["pta_ptnr"]["PTNR"] == 2
    assert r["decision"]["is_significant"] is True
    assert "IS-4" in r["decision"]["active_fattispecie"]


def test_scenario5_ricorrenza_scenario3():
    """Stesso scenario 3 ma ricorrenza attiva → PTNR≥4."""
    incident_data = {
        "service_disruption_hours": 1,
        "financial_impact_eur": 5_000,
        "affected_users_count": 10,
        "personal_data_involved": False,
        "cross_border_impact": False,
        "critical_infrastructure_impact": False,
        "incident_category": "other",
        "severity": "bassa",
    }
    r = run_full_classification(incident_data, CONFIG_IMPORTANTE, "importante", True)
    assert r["pta_ptnr"]["PTA"] == 2
    assert r["pta_ptnr"]["PTNR"] == 4
    assert r["decision"]["is_significant"] is True


def test_non_soggetto_forza_non_significativo():
    r = run_full_classification(
        {
            "service_disruption_hours": 100,
            "financial_impact_eur": 9_000_000,
            "affected_users_count": 10_000,
            "personal_data_involved": True,
            "cross_border_impact": True,
            "critical_infrastructure_impact": True,
            "incident_category": "data_breach",
            "severity": "critica",
        },
        CONFIG_IMPORTANTE,
        "non_soggetto",
        False,
    )
    assert r["decision"]["is_significant"] is False
