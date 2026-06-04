"""Step 0 — Centro Operativo: registry, advisor pilota, endpoint."""
import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.cockpit import insights as insights_mod
from apps.cockpit.insights import AdvisorContext, Insight, collect_insights
from apps.osint.advisors import enricher_key_health_advisor
from apps.cockpit.advisors_builtin import schedule_drift_advisor
from apps.osint.models import OsintSettings

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Modello Insight
# ---------------------------------------------------------------------------

class TestInsightModel:
    def test_fingerprint_stable_and_distinct(self):
        a = Insight(code="x.y", module="m", severity="warning",
                    entity_ref={"type": "t", "id": "1"})
        b = Insight(code="x.y", module="m", severity="warning",
                    entity_ref={"type": "t", "id": "1"})
        c = Insight(code="x.y", module="m", severity="warning",
                    entity_ref={"type": "t", "id": "2"})
        assert a.fingerprint == b.fingerprint
        assert a.fingerprint != c.fingerprint

    def test_to_dict_includes_fingerprint_and_params(self):
        d = Insight(code="x.y", module="m", severity="info", params={"n": 3}).to_dict()
        assert d["fingerprint"]
        assert d["params"] == {"n": 3}
        assert d["severity"] == "info"


# ---------------------------------------------------------------------------
# Registry + ordinamento per gravità
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_collect_sorts_by_severity(self, monkeypatch):
        def adv_info(_ctx):
            return [Insight(code="a", module="m", severity="info")]
        def adv_crit(_ctx):
            return [Insight(code="b", module="m", severity="critical")]
        monkeypatch.setattr(insights_mod, "_ADVISORS", [adv_info, adv_crit])
        monkeypatch.setattr(insights_mod, "_LOADED", True)
        out = collect_insights()
        assert [i.severity for i in out] == ["critical", "info"]

    def test_broken_advisor_does_not_break_others(self, monkeypatch):
        def adv_ok(_ctx):
            return [Insight(code="ok", module="m", severity="warning")]
        def adv_boom(_ctx):
            raise RuntimeError("kaboom")
        monkeypatch.setattr(insights_mod, "_ADVISORS", [adv_boom, adv_ok])
        monkeypatch.setattr(insights_mod, "_LOADED", True)
        out = collect_insights()
        assert [i.code for i in out] == ["ok"]


# ---------------------------------------------------------------------------
# Advisor OSINT — salute chiavi
# ---------------------------------------------------------------------------

class TestOsintAdvisor:
    def test_invalid_key_produces_insight(self):
        s = OsintSettings.load()
        s.enricher_health = {"virustotal": {"status": "invalid", "detail": "HTTP 401", "checked_at": "2026-06-04T00:00:00"}}
        s.save(update_fields=["enricher_health"])
        out = enricher_key_health_advisor(AdvisorContext())
        assert len(out) == 1
        assert out[0].code == "osint.key_invalid"
        assert out[0].params["provider"] == "virustotal"
        assert out[0].severity == "warning"

    def test_ok_and_no_key_produce_nothing(self):
        s = OsintSettings.load()
        s.enricher_health = {
            "virustotal": {"status": "ok", "detail": "HTTP 200", "checked_at": "x"},
            "hibp": {"status": "no_key", "detail": "", "checked_at": "x"},
        }
        s.save(update_fields=["enricher_health"])
        assert enricher_key_health_advisor(AdvisorContext()) == []

    def test_empty_health_is_safe(self):
        s = OsintSettings.load()
        s.enricher_health = {}
        s.save(update_fields=["enricher_health"])
        assert enricher_key_health_advisor(AdvisorContext()) == []


# ---------------------------------------------------------------------------
# Advisor schedule drift
# ---------------------------------------------------------------------------

class TestScheduleAdvisor:
    def test_drift_produces_insight(self):
        fake = [("osint-weekly-scan", "MISSING", "nessuna PeriodicTask"), ("x", "OK", "")]
        with patch("apps.audit_trail.management.commands.verify_schedule.evaluate_all", return_value=fake):
            out = schedule_drift_advisor(AdvisorContext())
        assert len(out) == 1
        assert out[0].code == "schedule.drift"
        assert out[0].params["count"] == 1
        assert out[0].params["jobs"][0]["name"] == "osint-weekly-scan"

    def test_all_ok_produces_nothing(self):
        fake = [("a", "OK", ""), ("b", "OK", "")]
        with patch("apps.audit_trail.management.commands.verify_schedule.evaluate_all", return_value=fake):
            assert schedule_drift_advisor(AdvisorContext()) == []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

class TestEndpoint:
    @pytest.fixture
    def client(self):
        user = User.objects.create_superuser(username="cock", password="p", email="c@t.com")
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_requires_auth(self):
        assert APIClient().get("/api/v1/cockpit/insights/").status_code in (401, 403)

    def test_returns_structure(self, client):
        resp = client.get("/api/v1/cockpit/insights/")
        assert resp.status_code == 200
        assert "insights" in resp.data
        assert set(resp.data["counts"]) == {"critical", "warning", "info", "total"}

    def test_surfaces_real_invalid_key(self, client):
        s = OsintSettings.load()
        s.enricher_health = {"gsb": {"status": "invalid", "detail": "HTTP 400", "checked_at": "x"}}
        s.save(update_fields=["enricher_health"])
        resp = client.get("/api/v1/cockpit/insights/")
        codes = [i["code"] for i in resp.data["insights"]]
        assert "osint.key_invalid" in codes
        assert resp.data["counts"]["total"] >= 1


# ---------------------------------------------------------------------------
# Servizio: ranking + Posture Score
# ---------------------------------------------------------------------------

class TestBuildCockpit:
    def _patch(self, monkeypatch, insights):
        from apps.cockpit import services
        monkeypatch.setattr(services, "collect_insights", lambda ctx: list(insights))

    def test_ranking_critical_first(self, monkeypatch):
        from apps.cockpit.services import build_cockpit
        self._patch(monkeypatch, [
            Insight(code="i", module="m", severity="info", area="governance"),
            Insight(code="c", module="m", severity="critical", area="supply_chain"),
            Insight(code="w", module="m", severity="warning", area="controls"),
        ])
        out = build_cockpit()
        assert [i["severity"] for i in out["insights"]] == ["critical", "warning", "info"]

    def test_posture_score(self, monkeypatch):
        from apps.cockpit.services import build_cockpit
        self._patch(monkeypatch, [
            Insight(code="c", module="m", severity="critical", area="supply_chain"),
            Insight(code="w", module="m", severity="warning", area="controls"),
        ])
        out = build_cockpit()
        assert out["posture"]["areas"]["supply_chain"]["score"] == 40
        assert out["posture"]["areas"]["controls"]["score"] == 15
        assert out["posture"]["areas"]["governance"]["score"] == 0
        # totale = media su 7 aree = (40+15)/7 arrotondato
        assert out["posture"]["total"] == round(55 / 7)
        assert out["counts"] == {"critical": 1, "warning": 1, "info": 0, "total": 2}

    def test_plant_filter_keeps_global_and_matching(self, monkeypatch):
        from apps.plants.models import Plant
        from apps.cockpit.services import build_cockpit
        p1 = Plant.objects.create(code="CKP1", name="P1", country="IT", nis2_scope="essenziale", status="attivo")
        self._patch(monkeypatch, [
            Insight(code="g", module="m", severity="warning", area="governance", plant_id=None),
            Insight(code="a", module="m", severity="warning", area="controls", plant_id=str(p1.pk)),
            Insight(code="b", module="m", severity="warning", area="controls", plant_id="other-uuid"),
        ])
        out = build_cockpit(plant=p1)
        codes = {i["code"] for i in out["insights"]}
        assert codes == {"g", "a"}  # globale + plant richiesto, non "other"


# ---------------------------------------------------------------------------
# Advisor cross-modulo (smoke su dati reali minimi)
# ---------------------------------------------------------------------------

class TestControlsAdvisor:
    def test_gap_controls_produce_insight(self):
        from django.utils import timezone
        from apps.plants.models import Plant, PlantFramework
        from apps.controls.models import Control, ControlInstance, Framework
        from apps.cockpit.advisors_builtin import controls_gap_advisor
        plant = Plant.objects.create(code="CKG1", name="GapPlant", country="IT", nis2_scope="essenziale", status="attivo")
        fw = Framework.objects.create(code="FW_CK", name="FW", version="1.0", published_at=timezone.localdate())
        # Il framework deve essere ATTIVO sul plant (il service canonico conta solo i framework attivi).
        PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate(), level="AL2", active=True)
        ctrl = Control.objects.create(framework=fw, external_id="CK-1", translations={}, level="L2")
        ControlInstance.objects.create(plant=plant, control=ctrl, status="gap")
        out = controls_gap_advisor(AdvisorContext())
        matching = [i for i in out if i.code == "controls.gap" and i.plant_id == str(plant.pk)]
        assert len(matching) == 1
        assert matching[0].params["count"] == 1
        assert matching[0].params["plant_name"] == "GapPlant"


class TestNewAdvisors:
    def test_risk_revaluation_canonical(self):
        from django.utils import timezone
        from apps.plants.models import Plant, PlantFramework
        from apps.controls.models import Control, ControlInstance, Framework
        from apps.cockpit.advisors_builtin import risk_revaluation_advisor
        plant = Plant.objects.create(code="CKR1", name="RevalPlant", country="IT", nis2_scope="essenziale", status="attivo")
        fw = Framework.objects.create(code="FW_REV", name="FW", version="1.0", published_at=timezone.localdate())
        PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate(), level="AL2", active=True)
        ctrl = Control.objects.create(framework=fw, external_id="REV-1", translations={}, level="L2")
        ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant", needs_revaluation=True)
        out = risk_revaluation_advisor(AdvisorContext())
        assert any(i.code == "risk.needs_revaluation" and i.plant_id == str(plant.pk) and i.params["count"] == 1 for i in out)

    def test_mgmt_review_overdue(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.plants.models import Plant
        from apps.management_review.models import ManagementReview
        from apps.cockpit.advisors_builtin import mgmt_review_overdue_advisor
        plant = Plant.objects.create(code="CKM1", name="MRPlant", country="IT", nis2_scope="essenziale", status="attivo")
        ManagementReview.objects.create(
            plant=plant, title="Riesame", status="pianificato",
            review_date=timezone.localdate() - timedelta(days=10),
        )
        out = mgmt_review_overdue_advisor(AdvisorContext())
        assert any(i.code == "mgmt_review.overdue" and i.plant_id == str(plant.pk) for i in out)

    def test_vacant_roles(self):
        from apps.cockpit.advisors_builtin import vacant_roles_advisor
        # DB di test vuoto → ruoli obbligatori NIS2/ISO tutti vacanti
        out = vacant_roles_advisor(AdvisorContext())
        assert any(i.code == "governance.vacant_roles" and i.severity == "critical" and i.params["count"] > 0 for i in out)

    def test_training_overdue(self):
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from apps.training.models import TrainingCourse, TrainingEnrollment
        from apps.cockpit.advisors_builtin import training_overdue_advisor
        u = get_user_model().objects.create_user(username="learner", password="p")
        course = TrainingCourse.objects.create(title="Sec Awareness", deadline=timezone.localdate() - timedelta(days=5), mandatory=True)
        TrainingEnrollment.objects.create(course=course, user=u, status="assegnato")
        out = training_overdue_advisor(AdvisorContext())
        assert any(i.code == "training.overdue" and i.params["count"] >= 1 for i in out)

    def test_documents_required_missing(self):
        from django.utils import timezone
        from apps.plants.models import Plant, PlantFramework
        from apps.controls.models import Framework
        from apps.compliance_schedule.models import RequiredDocument
        from apps.cockpit.advisors_builtin import documents_required_missing_advisor
        plant = Plant.objects.create(code="CKD1", name="DocPlant", country="IT", nis2_scope="essenziale", status="attivo")
        fw = Framework.objects.create(code="ISO27001", name="ISO", version="1.0", published_at=timezone.localdate())
        PlantFramework.objects.create(plant=plant, framework=fw, active_from=timezone.localdate(), level="AL2", active=True)
        # Documento obbligatorio richiesto ma NESSUN Document corrispondente → traffic red → mancante.
        RequiredDocument.objects.create(framework="ISO27001", document_type="policy", description="Security Policy", mandatory=True)
        out = documents_required_missing_advisor(AdvisorContext())
        match = [i for i in out if i.code == "documents.required_missing" and i.plant_id == str(plant.pk)]
        assert len(match) == 1
        assert match[0].params["count"] == 1

    def test_bcp_expired_untested(self):
        from apps.plants.models import Plant
        from apps.bcp.models import BcpPlan
        from apps.cockpit.advisors_builtin import bcp_expired_untested_advisor
        plant = Plant.objects.create(code="CKB1", name="BcpPlant", country="IT", nis2_scope="essenziale", status="attivo")
        # Piano approvato mai testato (last_test_date assente) → gap di continuità.
        BcpPlan.objects.create(plant=plant, title="BCP IT", status="approvato")
        out = bcp_expired_untested_advisor(AdvisorContext())
        assert any(i.code == "bcp.expired_untested" and i.plant_id == str(plant.pk) and i.params["count"] == 1 for i in out)

    def test_risk_open_high(self):
        from apps.plants.models import Plant
        from apps.risk.models import RiskAssessment
        from apps.cockpit.advisors_builtin import risk_open_high_advisor
        plant = Plant.objects.create(code="CKH1", name="RiskPlant", country="IT", nis2_scope="essenziale", status="attivo")
        # score 20 → weighted_score rosso (>14), aperto, non accettato formalmente.
        RiskAssessment.objects.create(plant=plant, status="completato", score=20, risk_accepted_formally=False)
        # Un rischio rosso accettato formalmente NON deve comparire.
        RiskAssessment.objects.create(plant=plant, status="completato", score=20, risk_accepted_formally=True)
        out = risk_open_high_advisor(AdvisorContext())
        match = [i for i in out if i.code == "risk.open_high" and i.plant_id == str(plant.pk)]
        assert len(match) == 1
        assert match[0].params["count"] == 1

    def test_risk_acceptance_expiring(self):
        from apps.plants.models import Plant
        from apps.risk.models import RiskAssessment
        from apps.cockpit.advisors_builtin import risk_acceptance_expiring_advisor
        from django.utils import timezone
        plant = Plant.objects.create(code="CKA1", name="AccPlant", country="IT", nis2_scope="essenziale", status="attivo")
        RiskAssessment.objects.create(
            plant=plant, status="completato", score=10,
            risk_accepted_formally=True, risk_acceptance_expiry=timezone.localdate(),
        )
        out = risk_acceptance_expiring_advisor(AdvisorContext())
        assert any(i.code == "risk.acceptance_expiring" and i.plant_id == str(plant.pk) and i.params["count"] == 1 for i in out)

    def test_incidents_nis2_deadline(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.plants.models import Plant
        from apps.incidents.models import Incident
        from apps.cockpit.advisors_builtin import incidents_nis2_deadline_advisor
        plant = Plant.objects.create(code="CKN1", name="IncPlant", country="IT", nis2_scope="essenziale", status="attivo")
        # Incidente significativo aperto, scadenza notifica formale già passata, mai notificato → critical.
        Incident.objects.create(
            plant=plant, title="Breach", description="x", detected_at=timezone.now(),
            severity="alta", nis2_notifiable="si", status="aperto",
            formal_notification_deadline=timezone.now() - timedelta(hours=1),
        )
        out = incidents_nis2_deadline_advisor(AdvisorContext())
        match = [i for i in out if i.code == "incidents.nis2_deadline" and i.plant_id == str(plant.pk)]
        assert len(match) == 1
        assert match[0].severity == "critical"


class TestSuppliersAssessmentAdvisor:
    def test_missing_items_one_row_with_categories(self):
        from apps.suppliers.models import Supplier
        from apps.cockpit.advisors_builtin import suppliers_assessment_advisor
        # Fornitore attivo senza questionario/NDA/valutazione → tutte e 3 mancano.
        Supplier.objects.create(name="ACME", status="attivo")
        out = suppliers_assessment_advisor(AdvisorContext())
        assert len(out) == 1  # UNA sola riga, non tre
        ins = out[0]
        assert ins.code == "suppliers.assessment_gaps"
        assert ins.params["count"] == 1
        keys = {c["key"] for c in ins.params["categories"]}
        assert keys == {"questionnaire", "nda", "evaluation"}

    def test_all_under_control_no_insight(self):
        from django.utils import timezone
        from datetime import timedelta
        from apps.suppliers.models import Supplier, SupplierQuestionnaire, SupplierInternalEvaluation
        from apps.documents.models import Document
        from apps.cockpit.advisors_builtin import suppliers_assessment_advisor
        s = Supplier.objects.create(name="OK Srl", status="attivo")
        now = timezone.now()
        SupplierQuestionnaire.objects.create(
            supplier=s, status="risposto", sent_at=now, last_sent_at=now, sent_to="a@b.it",
            expires_at=timezone.localdate() + timedelta(days=90),
        )
        Document.objects.create(title="NDA", category="contratto", document_type="contratto", status="approvato", supplier=s)
        SupplierInternalEvaluation.objects.create(
            supplier=s, score_impatto=1, score_accesso=1, score_dati=1, score_dipendenza=1,
            score_integrazione=1, score_compliance=1, weighted_score=1.0, risk_class="basso", is_current=True,
        )
        out = suppliers_assessment_advisor(AdvisorContext())
        assert out == []  # tutto presente e valido → sotto controllo


# ---------------------------------------------------------------------------
# Step 2 — persistenza, snooze/accept, snapshot
# ---------------------------------------------------------------------------

class TestPersistence:
    def _patch(self, monkeypatch, insights):
        from apps.cockpit import services
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: list(insights))

    def test_sync_create_resolve_reopen(self, monkeypatch):
        from apps.cockpit.services import sync_insights
        from apps.cockpit.models import InsightState, InsightStatus
        A = Insight(code="a", module="m", severity="warning", area="governance")
        B = Insight(code="b", module="m", severity="critical", area="risk")
        self._patch(monkeypatch, [A, B])
        assert sync_insights()["created"] == 2
        # B scompare → auto-resolve
        self._patch(monkeypatch, [A])
        assert sync_insights()["resolved"] == 1
        b = InsightState.objects.get(fingerprint=B.fingerprint)
        assert b.status == InsightStatus.RESOLVED
        # B ricompare → riapre
        self._patch(monkeypatch, [A, B])
        sync_insights()
        b.refresh_from_db()
        assert b.status == InsightStatus.OPEN

    def test_snooze_hides_then_expires(self, monkeypatch):
        from datetime import date, timedelta
        from apps.cockpit.services import build_cockpit, apply_insight_action
        A = Insight(code="a", module="m", severity="warning", area="governance")
        self._patch(monkeypatch, [A])
        assert build_cockpit()["counts"]["total"] == 1
        apply_insight_action(A.fingerprint, "snooze", until=date.today() + timedelta(days=5))
        out = build_cockpit()
        assert out["counts"]["total"] == 0 and out["suppressed_count"] == 1
        # snooze scaduto → riappare
        apply_insight_action(A.fingerprint, "snooze", until=date.today() - timedelta(days=1))
        assert build_cockpit()["counts"]["total"] == 1

    def test_accept_risk_hides_and_excluded_from_posture(self, monkeypatch):
        from datetime import date, timedelta
        from apps.cockpit.services import build_cockpit, apply_insight_action
        A = Insight(code="a", module="m", severity="critical", area="risk")
        self._patch(monkeypatch, [A])
        assert build_cockpit()["posture"]["areas"]["risk"]["score"] > 0
        apply_insight_action(A.fingerprint, "accept", until=date.today() + timedelta(days=30), note="ok")
        out = build_cockpit()
        assert out["counts"]["total"] == 0
        assert out["posture"]["areas"]["risk"]["score"] == 0  # accettato → non pesa

    def test_snapshot_recorded(self, monkeypatch):
        from apps.cockpit.services import record_posture_snapshot
        from apps.cockpit.models import PostureSnapshot
        A = Insight(code="a", module="m", severity="critical", area="risk")
        self._patch(monkeypatch, [A])
        record_posture_snapshot()
        org = PostureSnapshot.objects.filter(plant_id__isnull=True).first()
        assert org is not None and org.total > 0


class TestActionEndpoint:
    @pytest.fixture
    def client(self):
        user = User.objects.create_superuser(username="act", password="p", email="a@t.com")
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_snooze_endpoint(self, monkeypatch, client):
        from apps.cockpit import services
        A = Insight(code="a", module="m", severity="warning", area="governance")
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: [A])
        resp = client.post(f"/api/v1/cockpit/insights/{A.fingerprint}/snooze/", {"until": "2099-01-01"}, format="json")
        assert resp.status_code == 200
        assert resp.data["status"] == "snoozed"

    def test_invalid_action(self, client):
        resp = client.post("/api/v1/cockpit/insights/abc/frobnicate/", {}, format="json")
        assert resp.status_code == 400

    def test_unknown_fingerprint(self, monkeypatch, client):
        from apps.cockpit import services
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: [])
        resp = client.post("/api/v1/cockpit/insights/deadbeef/snooze/", {}, format="json")
        assert resp.status_code == 404


class TestAI:
    @pytest.fixture
    def client(self):
        user = User.objects.create_superuser(username="ai", password="p", email="ai@t.com")
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def _patch_insights(self, monkeypatch, insights):
        from apps.cockpit import services
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: list(insights))

    def test_explain_sanitizes_and_returns(self, monkeypatch):
        import apps.ai_engine.router as router
        from apps.cockpit.services import ai_explain_insight
        calls = {}
        monkeypatch.setattr(router, "route", lambda **kw: calls.update(kw) or {"text": "spiegazione", "provider": "ollama", "used_fallback": True})
        A = Insight(code="a", module="m", severity="warning", area="governance", plant_id="p1",
                    compliance_refs=[{"framework": "NIS2", "control": "art.21"}])
        self._patch_insights(monkeypatch, [A])
        out = ai_explain_insight(A.fingerprint)
        assert out["text"] == "spiegazione"
        assert calls["sanitize"] is True            # regola #9: mai PII al cloud in chiaro
        assert calls["plant_ids"] == ["p1"]

    def test_explain_unknown_returns_none(self, monkeypatch):
        from apps.cockpit.services import ai_explain_insight
        self._patch_insights(monkeypatch, [])
        assert ai_explain_insight("nope") is None

    def test_assistant_is_grounded(self, monkeypatch):
        import apps.ai_engine.router as router
        from apps.cockpit import services
        captured = {}
        monkeypatch.setattr(router, "route", lambda **kw: captured.update(kw) or {"text": "risposta"})
        A = Insight(code="controls.gap", module="m", severity="warning", area="controls")
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: [A])
        out = services.ai_assistant("quali problemi?")
        assert out["text"] == "risposta"
        assert "controls.gap" in captured["prompt"]  # grounding sugli insight reali
        assert captured["sanitize"] is True

    def test_explain_endpoint_503_when_llm_down(self, monkeypatch, client):
        import apps.ai_engine.router as router
        from apps.cockpit import services
        from apps.ai_engine.router import LlmUnavailable
        A = Insight(code="a", module="m", severity="warning", area="governance")
        monkeypatch.setattr(services, "collect_insights", lambda ctx=None: [A])
        def boom(**kw):
            raise LlmUnavailable("down")
        monkeypatch.setattr(router, "route", boom)
        resp = client.post(f"/api/v1/cockpit/insights/{A.fingerprint}/explain/", {}, format="json")
        assert resp.status_code == 503

    def test_assistant_endpoint_requires_question(self, client):
        resp = client.post("/api/v1/cockpit/assistant/", {}, format="json")
        assert resp.status_code == 400
