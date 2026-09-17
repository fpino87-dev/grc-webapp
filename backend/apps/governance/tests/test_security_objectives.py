"""Obiettivi di sicurezza (ISO/IEC 27001 §6.2) — servizi, ciclo di vita, API."""
import pytest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

User = get_user_model()

URL = "/api/v1/governance/security-objectives/"


# ── Fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="OBJ-P1", name="Plant Obiettivi", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def ciso(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="obj_ciso", email="objciso@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    return u


@pytest.fixture
def auditor(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="obj_aud", email="objaud@test.com", password="test")
    UserPlantAccess.objects.create(user=u, role=GrcRole.EXTERNAL_AUDITOR, scope_type="org")
    return u


@pytest.fixture
def plant_manager(db, plant):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="obj_pm", email="objpm@test.com", password="test")
    access = UserPlantAccess.objects.create(user=u, role=GrcRole.PLANT_MANAGER, scope_type="single_plant")
    access.scope_plants.add(plant)
    return u


@pytest.fixture
def client(ciso):
    c = APIClient()
    c.force_authenticate(user=ciso)
    return c


@pytest.fixture
def kpi(db, plant):
    from apps.tasks.models import KPIDefinition
    return KPIDefinition.objects.create(
        kpi_code="patch_coverage", name="Copertura patch critiche", unit="%",
        source="internal", plant=plant, aggregation="last_value",
        threshold_direction="above", threshold_warning=60.0, threshold_critical=50.0,
    )


def _objective(plant=None, **kw):
    """Obiettivo manuale di default: 40 → 90 in 100 giorni."""
    from apps.governance.models import SecurityObjective
    today = kw.pop("today", date(2026, 1, 1))
    data = dict(
        code=kw.pop("code", "OBJ-2026-01"), title="Copertura patch critiche",
        measure_source="manual", unit="%", start_date=today,
        baseline_value=40.0, target_value=90.0, target_direction="above",
        target_date=today + timedelta(days=100), owner_role="plant_manager",
        evaluation_method="Misura mensile dalla console patch.", status="attivo",
    )
    data.update(kw)
    return SecurityObjective.objects.create(plant=plant, **data)


# ── Progresso e traiettoria ───────────────────────────────────────────────

@pytest.mark.django_db
def test_progress_direction_above():
    from apps.governance.services import objective_progress_pct
    obj = _objective()
    assert objective_progress_pct(obj, 40.0) == 0.0
    assert objective_progress_pct(obj, 65.0) == 50.0
    assert objective_progress_pct(obj, 90.0) == 100.0


@pytest.mark.django_db
def test_progress_direction_below():
    """Obiettivo che deve scendere (es. giorni dall'ultimo test di ripristino):
    stessa formula, progresso positivo quando si migliora."""
    from apps.governance.services import objective_progress_pct
    obj = _objective(baseline_value=90.0, target_value=30.0, target_direction="below")
    assert objective_progress_pct(obj, 60.0) == 50.0
    assert objective_progress_pct(obj, 30.0) == 100.0


@pytest.mark.django_db
def test_progress_negative_when_worse_than_baseline():
    """Peggio del punto di partenza è un'informazione, non uno zero."""
    from apps.governance.services import objective_progress_pct
    obj = _objective()
    assert objective_progress_pct(obj, 30.0) == -20.0


@pytest.mark.django_db
def test_progress_none_without_baseline():
    from apps.governance.services import objective_progress_pct
    assert objective_progress_pct(_objective(baseline_value=None), 70.0) is None


@pytest.mark.django_db
def test_track_at_risk_when_behind_schedule():
    """Metà tempo consumato, nessun progresso → traiettoria a rischio anche se
    il valore è ancora sopra la soglia di warning del KPI."""
    from apps.governance.services import TRACK_AT_RISK, evaluate_objective
    obj = _objective()
    ev = evaluate_objective(obj, value=42.0, measured_on=date(2026, 2, 20),
                            today=date(2026, 2, 20))
    assert ev["track"] == TRACK_AT_RISK
    assert ev["elapsed_pct"] == 50.0


@pytest.mark.django_db
def test_track_on_track_within_tolerance():
    from apps.governance.services import TRACK_ON_TRACK, evaluate_objective
    obj = _objective()
    ev = evaluate_objective(obj, value=62.0, measured_on=date(2026, 2, 20),
                            today=date(2026, 2, 20))
    assert ev["track"] == TRACK_ON_TRACK


@pytest.mark.django_db
def test_track_missed_after_target_date():
    from apps.governance.services import TRACK_MISSED, evaluate_objective
    obj = _objective()
    ev = evaluate_objective(obj, value=80.0, measured_on=date(2026, 5, 1),
                            today=date(2026, 5, 1))
    assert ev["track"] == TRACK_MISSED
    assert ev["days_to_target"] < 0


@pytest.mark.django_db
def test_track_reached_before_target_date():
    from apps.governance.services import TRACK_ON_TRACK, evaluate_objective
    obj = _objective()
    ev = evaluate_objective(obj, value=95.0, measured_on=date(2026, 2, 1),
                            today=date(2026, 2, 1))
    assert ev["reached"] is True
    assert ev["track"] == TRACK_ON_TRACK


@pytest.mark.django_db
def test_track_no_data_without_measures():
    from apps.governance.services import TRACK_NO_DATA, evaluate_objective
    ev = evaluate_objective(_objective(), today=date(2026, 2, 1))
    assert ev["track"] == TRACK_NO_DATA


@pytest.mark.django_db
def test_weak_target_flagged_against_kpi_warning(plant, kpi):
    """Un target che non supera la soglia di warning del KPI non aggiunge nulla
    a ciò che il KPI già segnala: va mostrato a chi lo configura."""
    from apps.governance.services import evaluate_objective
    weak = _objective(plant=plant, code="OBJ-W", measure_source="kpi",
                      kpi_definition=kpi, unit="", target_value=58.0)
    strong = _objective(plant=plant, code="OBJ-S", measure_source="kpi",
                        kpi_definition=kpi, unit="", target_value=95.0)
    assert evaluate_objective(weak, today=date(2026, 2, 1))["weak_target"] is True
    assert evaluate_objective(strong, today=date(2026, 2, 1))["weak_target"] is False


# ── Lettura delle misure ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_latest_value_from_kpi_snapshot(plant, kpi):
    """Obiettivo agganciato a un KPI: il valore arriva dagli snapshot M08,
    senza che nessuno lo riscriva."""
    from apps.tasks.models import OperationalKpiSnapshot
    from apps.governance.services import latest_objective_values
    OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plant, week_start=date(2026, 1, 5),
        value=55.0, status="ok", source="internal",
    )
    OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plant, week_start=date(2026, 2, 2),
        value=71.0, status="ok", source="internal",
    )
    obj = _objective(plant=plant, measure_source="kpi", kpi_definition=kpi, unit="")
    assert latest_objective_values([obj])[obj.id] == (71.0, date(2026, 2, 2))


@pytest.mark.django_db
def test_series_merges_sources(plant, ciso):
    from apps.governance.services import objective_series, record_objective_measurement
    obj = _objective(plant=plant)
    record_objective_measurement(obj, ciso, value=50.0, measured_on=date(2026, 1, 31))
    record_objective_measurement(obj, ciso, value=60.0, measured_on=date(2026, 2, 28))
    series = objective_series(obj)
    assert [p["value"] for p in series] == [50.0, 60.0]


@pytest.mark.django_db
def test_measurement_refused_on_kpi_backed_objective(plant, kpi, ciso):
    """Due verità sullo stesso numero: vietato per costruzione."""
    from apps.governance.services import record_objective_measurement
    obj = _objective(plant=plant, measure_source="kpi", kpi_definition=kpi, unit="")
    with pytest.raises(ValidationError):
        record_objective_measurement(obj, ciso, value=70.0)


@pytest.mark.django_db
def test_measurement_is_upserted_per_day(plant, ciso):
    from apps.governance.models import SecurityObjectiveMeasurement
    from apps.governance.services import record_objective_measurement
    obj = _objective(plant=plant)
    record_objective_measurement(obj, ciso, value=50.0, measured_on=date(2026, 1, 31))
    record_objective_measurement(obj, ciso, value=55.0, measured_on=date(2026, 1, 31))
    rows = SecurityObjectiveMeasurement.objects.filter(objective=obj)
    assert rows.count() == 1 and rows.first().value == 55.0


# ── Ciclo di vita ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_activate_requires_owner_and_evaluation_method(plant, ciso):
    from apps.governance.services import activate_objective
    obj = _objective(plant=plant, status="bozza", owner_role="", evaluation_method="")
    with pytest.raises(ValidationError):
        activate_objective(obj, ciso)
    obj.owner_role = "plant_manager"
    obj.evaluation_method = "Misura mensile."
    activate_objective(obj, ciso)
    obj.refresh_from_db()
    assert obj.status == "attivo"


@pytest.mark.django_db
def test_close_sets_outcome_and_is_final(plant, ciso):
    from apps.governance.services import close_objective
    obj = _objective(plant=plant)
    close_objective(obj, ciso, outcome="non_raggiunto", note="Budget non approvato.")
    obj.refresh_from_db()
    assert obj.status == "non_raggiunto" and obj.closed_by_id == ciso.id
    with pytest.raises(ValidationError):
        close_objective(obj, ciso, outcome="raggiunto")


@pytest.mark.django_db
def test_cancel_requires_reason(plant, ciso):
    from apps.governance.services import close_objective
    with pytest.raises(ValidationError):
        close_objective(_objective(plant=plant), ciso, outcome="annullato")


@pytest.mark.django_db
def test_close_writes_audit_log(plant, ciso):
    from core.audit import AuditLog
    from apps.governance.services import close_objective
    close_objective(_objective(plant=plant), ciso, outcome="raggiunto")
    assert AuditLog.objects.filter(action_code="governance.security_objective.close").exists()


# ── Validazioni di coerenza ───────────────────────────────────────────────

@pytest.mark.django_db
def test_target_must_improve_baseline(client, plant):
    resp = client.post(URL, {
        "code": "OBJ-BAD", "title": "Target che peggiora", "plant": str(plant.id),
        "measure_source": "manual", "unit": "%", "start_date": "2026-01-01",
        "baseline_value": 80.0, "target_value": 60.0, "target_direction": "above",
        "target_date": "2026-12-31", "owner_role": "plant_manager",
    }, format="json")
    assert resp.status_code == 400 and "target_value" in resp.data


@pytest.mark.django_db
def test_org_objective_cannot_use_plant_kpi(client, kpi):
    resp = client.post(URL, {
        "code": "OBJ-ORG", "title": "Obiettivo org su KPI di sito",
        "measure_source": "kpi", "kpi_definition": str(kpi.id),
        "start_date": "2026-01-01", "baseline_value": 40.0, "target_value": 90.0,
        "target_date": "2026-12-31", "owner_role": "plant_manager",
    }, format="json")
    assert resp.status_code == 400 and "kpi_definition" in resp.data


@pytest.mark.django_db
def test_duplicate_code_in_same_scope_refused(client, plant):
    _objective(plant=plant, code="OBJ-DUP")
    resp = client.post(URL, {
        "code": "OBJ-DUP", "title": "Doppione", "plant": str(plant.id),
        "measure_source": "manual", "unit": "%", "start_date": "2026-01-01",
        "baseline_value": 40.0, "target_value": 90.0, "target_date": "2026-12-31",
        "owner_role": "plant_manager",
    }, format="json")
    assert resp.status_code == 400 and "code" in resp.data


# ── API e permessi ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_and_list(client, plant):
    resp = client.post(URL, {
        "code": "OBJ-2026-07", "title": "Fornitori critici con NDA chiuso",
        "plant": str(plant.id), "measure_source": "manual", "unit": "%",
        "start_date": "2026-01-01", "baseline_value": 48.0, "target_value": 100.0,
        "target_date": "2026-06-30", "owner_role": "compliance_officer",
        "evaluation_method": "Conteggio trimestrale.",
    }, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "bozza"
    listing = client.get(URL)
    assert listing.status_code == 200
    row = listing.data["results"][0] if "results" in listing.data else listing.data[0]
    assert row["evaluation"]["track"] == "senza_misure"


@pytest.mark.django_db
def test_status_not_writable_from_patch(client, plant):
    """Il ciclo di vita passa dalle azioni dedicate, che validano e auditano."""
    obj = _objective(plant=plant, status="bozza")
    resp = client.patch(f"{URL}{obj.id}/", {"status": "raggiunto"}, format="json")
    assert resp.status_code == 200
    obj.refresh_from_db()
    assert obj.status == "bozza"


@pytest.mark.django_db
def test_closed_objective_is_not_editable(client, plant, ciso):
    from apps.governance.services import close_objective
    obj = _objective(plant=plant)
    close_objective(obj, ciso, outcome="raggiunto")
    resp = client.patch(f"{URL}{obj.id}/", {"title": "Nuovo titolo"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_external_auditor_reads_but_cannot_write(auditor, plant):
    c = APIClient()
    c.force_authenticate(user=auditor)
    _objective(plant=plant)
    assert c.get(URL).status_code == 200
    resp = c.post(URL, {
        "code": "OBJ-X", "title": "Non consentito", "plant": str(plant.id),
        "measure_source": "manual", "start_date": "2026-01-01",
        "target_value": 90.0, "target_date": "2026-12-31",
    }, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_plant_manager_can_record_measure_but_not_create(plant_manager, plant):
    c = APIClient()
    c.force_authenticate(user=plant_manager)
    obj = _objective(plant=plant)
    resp = c.post(f"{URL}{obj.id}/measure/", {"value": 55.0, "measured_on": "2026-02-01"},
                  format="json")
    assert resp.status_code == 201
    assert c.post(URL, {
        "code": "OBJ-PM", "title": "Non consentito", "plant": str(plant.id),
        "measure_source": "manual", "start_date": "2026-01-01",
        "target_value": 90.0, "target_date": "2026-12-31",
    }, format="json").status_code == 403


@pytest.mark.django_db
def test_plant_scoping_hides_other_sites(plant_manager, plant, db):
    from apps.plants.models import Plant
    other = Plant.objects.create(code="OBJ-P2", name="Altro sito", country="IT",
                                 nis2_scope="non_soggetto", status="attivo")
    _objective(plant=plant, code="OBJ-MINE")
    _objective(plant=other, code="OBJ-OTHER")
    _objective(plant=None, code="OBJ-ORG-WIDE")
    c = APIClient()
    c.force_authenticate(user=plant_manager)
    data = c.get(URL).data
    rows = data["results"] if "results" in data else data
    codes = {r["code"] for r in rows}
    # L'obiettivo di organizzazione resta visibile: è un impegno aziendale.
    assert codes == {"OBJ-MINE", "OBJ-ORG-WIDE"}


@pytest.mark.django_db
def test_overview_counts_by_track(client, plant):
    _objective(plant=plant, code="OBJ-A")
    _objective(plant=plant, code="OBJ-B", status="raggiunto")
    resp = client.get(f"{URL}overview/")
    assert resp.status_code == 200
    assert resp.data["totale"] == 2
    assert resp.data["per_stato"]["raggiunto"] == 1


@pytest.mark.django_db
def test_list_query_count_does_not_grow_with_rows(client, plant):
    """Regola #6: i valori correnti si caricano in blocco, non per riga.

    Si confronta il numero di query fra 3 e 12 obiettivi invece di fissare un
    numero assoluto: il numero assoluto cambia al primo middleware in più, il
    fatto che non cresca con le righe è ciò che conta davvero.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    for i in range(3):
        _objective(plant=plant, code=f"OBJ-N{i}")
    with CaptureQueriesContext(connection) as few:
        assert client.get(URL).status_code == 200

    for i in range(3, 12):
        _objective(plant=plant, code=f"OBJ-N{i}")
    with CaptureQueriesContext(connection) as many:
        assert client.get(URL).status_code == 200

    assert len(many.captured_queries) == len(few.captured_queries)


@pytest.mark.django_db
def test_lifecycle_actions_over_api(client, plant):
    """Attiva → sospendi → riattiva → chiudi, tutto dalle azioni dedicate."""
    obj = _objective(plant=plant, status="bozza")
    assert client.post(f"{URL}{obj.id}/activate/").data["status"] == "attivo"
    assert client.post(f"{URL}{obj.id}/suspend/", {"note": "Fermo per budget."},
                       format="json").data["status"] == "sospeso"
    assert client.post(f"{URL}{obj.id}/activate/").data["status"] == "attivo"
    closed = client.post(f"{URL}{obj.id}/close/", {"outcome": "raggiunto"}, format="json")
    assert closed.data["status"] == "raggiunto"


@pytest.mark.django_db
def test_close_with_invalid_outcome_is_400(client, plant):
    obj = _objective(plant=plant)
    assert client.post(f"{URL}{obj.id}/close/", {"outcome": "boh"},
                       format="json").status_code == 400


@pytest.mark.django_db
def test_suspend_refused_on_draft(client, plant):
    obj = _objective(plant=plant, status="bozza")
    assert client.post(f"{URL}{obj.id}/suspend/").status_code == 400


@pytest.mark.django_db
def test_series_endpoint_returns_points(client, plant, ciso):
    from apps.governance.services import record_objective_measurement
    obj = _objective(plant=plant)
    record_objective_measurement(obj, ciso, value=50.0, measured_on=date(2026, 1, 31))
    resp = client.get(f"{URL}{obj.id}/series/")
    assert resp.status_code == 200
    assert resp.data["items"] == [{"date": "2026-01-31", "value": 50.0}]


@pytest.mark.django_db
def test_measure_with_malformed_date_is_400(client, plant):
    obj = _objective(plant=plant)
    resp = client.post(f"{URL}{obj.id}/measure/", {"value": 50.0, "measured_on": "31-01-2026"},
                       format="json")
    assert resp.status_code == 400 and "measured_on" in resp.data


@pytest.mark.django_db
def test_measure_before_period_start_is_400(client, plant):
    obj = _objective(plant=plant)
    resp = client.post(f"{URL}{obj.id}/measure/", {"value": 50.0, "measured_on": "2025-12-01"},
                       format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_target_change_on_active_objective_is_audited(client, plant):
    """Un target che si sposta senza lasciare traccia svuota l'impegno."""
    from core.audit import AuditLog
    obj = _objective(plant=plant)
    assert client.patch(f"{URL}{obj.id}/", {"target_value": 70.0},
                        format="json").status_code == 200
    log = AuditLog.objects.filter(action_code="governance.security_objective.update").last()
    assert log.payload["changed"]["target_value"] == {"da": 90.0, "a": 70.0}


@pytest.mark.django_db
def test_reached_and_weak_target_with_below_direction(plant, kpi):
    """Direzione «sotto il target»: raggiunto significa essere scesi, e la
    soglia di warning si confronta al contrario."""
    from apps.governance.services import evaluate_objective, objective_is_reached
    kpi.threshold_direction = "below"
    kpi.threshold_warning = 30.0
    kpi.save(update_fields=["threshold_direction", "threshold_warning"])
    obj = _objective(plant=plant, code="OBJ-DOWN", measure_source="kpi", kpi_definition=kpi,
                     unit="", baseline_value=75.0, target_value=20.0, target_direction="below")
    assert objective_is_reached(obj, 18.0) is True
    assert objective_is_reached(obj, 25.0) is False
    assert evaluate_objective(obj, today=date(2026, 2, 1))["weak_target"] is False

    obj.target_value = 45.0  # peggiore della soglia di warning: non aggiunge nulla
    assert evaluate_objective(obj, today=date(2026, 2, 1))["weak_target"] is True


@pytest.mark.django_db
def test_list_shows_current_value_from_manual_measures(client, plant, ciso):
    from apps.governance.services import record_objective_measurement
    obj = _objective(plant=plant, code="OBJ-MAN")
    record_objective_measurement(obj, ciso, value=65.0, measured_on=date(2026, 2, 20))
    data = client.get(URL).data
    row = (data["results"] if "results" in data else data)[0]
    assert row["evaluation"]["current_value"] == 65.0
    assert row["evaluation"]["progress_pct"] == 50.0
    assert row["evaluation"]["unit"] == "%"


@pytest.mark.django_db
def test_series_from_kpi_snapshots(plant, kpi):
    """Obiettivo su KPI: la serie sono gli snapshot settimanali di M08, senza
    che nessuna misura venga copiata in governance."""
    from apps.tasks.models import OperationalKpiSnapshot
    from apps.governance.services import objective_series
    for week, value in [(date(2026, 1, 5), 55.0), (date(2026, 2, 2), 71.0)]:
        OperationalKpiSnapshot.objects.create(
            kpi_definition=kpi, plant=plant, week_start=week, value=value,
            status="ok", source="internal",
        )
    # Prima dell'inizio del periodo: fuori dalla finestra dell'impegno.
    OperationalKpiSnapshot.objects.create(
        kpi_definition=kpi, plant=plant, week_start=date(2025, 12, 1), value=20.0,
        status="critical", source="internal",
    )
    obj = _objective(plant=plant, code="OBJ-KPI", measure_source="kpi",
                     kpi_definition=kpi, unit="")
    assert [p["value"] for p in objective_series(obj)] == [55.0, 71.0]


@pytest.mark.django_db
def test_no_baseline_means_no_trajectory_judgement(plant):
    """Senza valore di partenza non si inventa un giudizio sull'andamento."""
    from apps.governance.services import TRACK_NO_DATA, evaluate_objective
    obj = _objective(plant=plant, baseline_value=None)
    ev = evaluate_objective(obj, value=55.0, measured_on=date(2026, 2, 20),
                            today=date(2026, 2, 20))
    assert ev["progress_pct"] is None and ev["track"] == TRACK_NO_DATA


@pytest.mark.django_db
def test_kpi_backed_objective_needs_a_kpi(client, plant):
    resp = client.post(URL, {
        "code": "OBJ-NOKPI", "title": "Senza KPI", "plant": str(plant.id),
        "measure_source": "kpi", "start_date": "2026-01-01",
        "baseline_value": 40.0, "target_value": 90.0, "target_date": "2026-12-31",
    }, format="json")
    assert resp.status_code == 400 and "kpi_definition" in resp.data
