"""
Test C14 — calc_suggested_status rispetta la decisione manuale N/A.

Un controllo valutato N/A (non applicabile) è una decisione di governance
deliberata e documentata. Il suggeritore evidence-based non deve proporre un
cambio di stato: prima del fix, mancando le evidenze, suggeriva "gap" e la UI
mostrava il badge "→ gap" + il box "Applica suggerimento" su una scelta presa
consapevolmente.
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def make_instance(db):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.plants.models import Plant, PlantFramework

    user = User.objects.create_user(username="sug_user", email="sug@test.com", password="test")
    plant = Plant.objects.create(
        code="SUG-P", name="Plant Suggest", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    fw = Framework.objects.create(
        code="ISO27001", name="ISO 27001", version="2022",
        published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw,
        active_from=timezone.localdate(), level="L2", active=True,
    )

    counter = {"n": 0}

    def _make(status):
        counter["n"] += 1
        n = counter["n"]
        control = Control.objects.create(
            framework=fw, external_id=f"SUG-{n}",
            translations={"it": {"title": f"Controllo {n}"}},
            evidence_requirement={
                "min_evidences": 1,
                "evidences": [{"type": "report", "mandatory": True, "description": "Report"}],
            },
        )
        return ControlInstance.objects.create(
            plant=plant, control=control, status=status, created_by=user,
        )

    return _make


@pytest.mark.django_db
def test_na_control_suggests_no_change(make_instance):
    """Un controllo N/A senza evidenze non viene suggerito a 'gap': resta 'na'."""
    from apps.controls.services import calc_suggested_status

    inst = make_instance("na")
    assert calc_suggested_status(inst) == "na"


@pytest.mark.django_db
def test_non_na_control_still_suggested_from_evidence(make_instance):
    """Il fix N/A non altera il suggerimento per gli altri stati: senza evidenze → gap."""
    from apps.controls.services import calc_suggested_status

    inst = make_instance("non_valutato")
    assert calc_suggested_status(inst) == "gap"


@pytest.mark.django_db
def test_na_control_has_no_requirement_gaps(make_instance):
    """Un controllo N/A è fuori ambito: niente documenti/evidenze mancanti."""
    from apps.controls.services import check_evidence_requirements

    inst = make_instance("na")  # ha un requisito (min_evidences) ma nessuna evidenza
    res = check_evidence_requirements(inst)
    assert res["not_applicable"] is True
    assert res["satisfied"] is True
    assert res["missing_documents"] == []
    assert res["missing_evidences"] == []
    assert res["expired_evidences"] == []


@pytest.mark.django_db
def test_non_na_control_still_flags_gaps(make_instance):
    """Per gli stati non-N/A le mancanze continuano a essere segnalate."""
    from apps.controls.services import check_evidence_requirements

    inst = make_instance("non_valutato")
    res = check_evidence_requirements(inst)
    assert res["not_applicable"] is False
    assert res["satisfied"] is False
    assert res["missing_evidences"]  # requisito non soddisfatto
