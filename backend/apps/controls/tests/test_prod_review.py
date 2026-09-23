"""Review prod-readiness M03 (pass leggero, 2026-06-13).

Il default destroy di ControlViewSet faceva HARD delete del Control →
CASCADE (FK on_delete=CASCADE) su tutte le ControlInstance valutate, perdita
dati su tutti i siti. Ora soft delete + audit: le istanze sopravvivono.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_grc.models import GrcRole, UserPlantAccess

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(username="m3admin", email="m3@a.test", password="x")
    UserPlantAccess.objects.create(user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_control_with_evaluations_is_blocked_not_deleted(admin_client):
    """Guard: un controllo con valutazioni NON si elimina (niente catena rotta
    né perdita dati). Si gestisce via load_frameworks."""
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant

    fw = Framework.objects.create(code="M3FW", name="M3 FW", version="1", published_at=datetime.date.today())
    ctrl = Control.objects.create(framework=fw, external_id="M3.1", translations={"it": {"title": "T"}})
    plant = Plant.objects.create(code="M3P", name="M3 Plant", country="IT", nis2_scope="importante", status="attivo")
    inst = ControlInstance.objects.create(plant=plant, control=ctrl, status="compliant")

    resp = admin_client.delete(f"/api/v1/controls/controls/{ctrl.id}/")
    assert resp.status_code == 400
    # Controllo e istanza intatti (niente hard cascade, niente soft delete)
    assert Control.objects.filter(pk=ctrl.id, deleted_at__isnull=True).exists()
    assert ControlInstance.objects.filter(pk=inst.id, deleted_at__isnull=True).exists()


@pytest.mark.django_db
def test_control_without_evaluations_is_soft_deleted(admin_client):
    from apps.controls.models import Control, Framework
    from core.audit import AuditLog

    fw = Framework.objects.create(code="M3FW2", name="M3 FW2", version="1", published_at=datetime.date.today())
    ctrl = Control.objects.create(framework=fw, external_id="M3.2", translations={"it": {"title": "T"}})

    resp = admin_client.delete(f"/api/v1/controls/controls/{ctrl.id}/")
    assert resp.status_code == 204
    assert Control.objects.all_with_deleted().filter(pk=ctrl.id, deleted_at__isnull=False).exists()
    assert AuditLog.objects.filter(action_code="controls.control.delete").exists()


@pytest.mark.django_db
def test_generated_procedure_docx_is_marked_as_ai(monkeypatch):
    """AI Act art. 50: il .docx generato dichiara di essere opera dell'IA,
    sotto il titolo e nelle proprietà del file."""
    import io

    from docx import Document

    from apps.ai_engine import router
    from apps.controls.models import Control, Framework
    from apps.controls.services import generate_procedure_document

    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1",
                                  translations={"en": {"title": "Policies"}})
    monkeypatch.setattr(router, "route", lambda **kw: {
        "text": "## Scope\nText", "provider": "anthropic", "model": "m1",
    })

    doc = Document(io.BytesIO(generate_procedure_document(ctrl, "en", None)))
    notice = "Document generated with AI (anthropic/m1): draft to be reviewed and approved before use."
    assert doc.paragraphs[1].text == notice
    assert doc.core_properties.comments == notice
    assert doc.core_properties.keywords == "AI-generated"


def _summary_control():
    from apps.controls.models import Control, Framework

    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1",
                                  published_at=datetime.date(2024, 1, 1))
    return Control.objects.create(framework=fw, external_id="A.5.1", translations={
        "it": {"title": "Politiche", "description": "Definire le politiche",
               "practical_summary": "Riassunto in italiano"},
        "fr": {"practical_summary": "Résumé en français"},
    })


@pytest.mark.django_db
def test_detail_shows_practical_summary_only_in_requested_language(admin_client):
    """Il riassunto IA è per lingua: niente ripiego sull'italiano, così la UI
    propone di generarlo invece di mostrarlo nella lingua sbagliata."""
    from apps.controls.models import ControlInstance
    from apps.plants.models import Plant

    plant = Plant.objects.create(code="M3P", name="M3 Plant", country="IT", nis2_scope="importante", status="attivo")
    from apps.plants.models import PlantFramework

    ctrl = _summary_control()
    PlantFramework.objects.create(plant=plant, framework=ctrl.framework,
                                  active_from=datetime.date(2024, 1, 1))
    inst = ControlInstance.objects.create(plant=plant, control=ctrl)
    url = f"/api/v1/controls/instances/{inst.id}/detail-info/"

    def summary(lang):
        r = admin_client.get(url, {"lang": lang})
        assert r.status_code == 200, r.data
        return r.data["practical_summary"]

    assert summary("it") == "Riassunto in italiano"
    assert summary("fr") == "Résumé en français"
    assert summary("pl") == ""


@pytest.mark.django_db
def test_explain_prompt_keeps_description_when_language_has_only_summary(admin_client, monkeypatch):
    from apps.ai_engine import tasks_ai

    ctrl = _summary_control()
    prompts = []

    def fake_route(**kw):
        prompts.append(kw["prompt"])
        return {"text": '{"summary": "Nouveau résumé"}'}

    monkeypatch.setattr(tasks_ai, "route", fake_route)
    r = admin_client.post(f"/api/v1/controls/controls/{ctrl.id}/explain/", {"lang": "fr"}, format="json")
    assert r.status_code == 200
    assert "Definire le politiche" in prompts[0] and "in français" in prompts[0]
    ctrl.refresh_from_db()
    assert ctrl.translations["fr"]["practical_summary"] == "Nouveau résumé"

    admin_client.post(f"/api/v1/controls/controls/{ctrl.id}/explain/", {"lang": "zz-evil"}, format="json")
    ctrl.refresh_from_db()
    assert set(ctrl.translations) == {"it", "fr"}


@pytest.mark.django_db
def test_explain_errors_do_not_leak_exception_text(admin_client, monkeypatch):
    """CodeQL py/stack-trace-exposure: il testo di un'eccezione imprevista resta
    nel log; "IA non configurata" ha un messaggio fisso, non quello dell'eccezione."""
    from apps.ai_engine import tasks_ai
    from apps.ai_engine.router import AiNotConfigured

    ctrl = _summary_control()
    url = f"/api/v1/controls/controls/{ctrl.id}/explain/"

    def boom(**kw):
        raise RuntimeError("dettaglio interno /srv/app/secret.py")

    monkeypatch.setattr(tasks_ai, "route", boom)
    r = admin_client.post(url, {"lang": "it"}, format="json")
    assert r.status_code == 500 and "secret" not in str(r.data)

    def not_configured(**kw):
        raise AiNotConfigured("testo interno")

    monkeypatch.setattr(tasks_ai, "route", not_configured)
    r = admin_client.post(url, {"lang": "it"}, format="json")
    assert r.status_code == 400
    assert r.data["error"].startswith("Nessuna configurazione IA attiva")
