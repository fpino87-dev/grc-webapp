"""
Test C3 — calc_maturity_level: la maturità auto-calcolata è limitata a 4.

Il livello 5 VDA ISA (ottimizzato, miglioramento continuo) non è derivabile da
uno status self-assessment: si ottiene solo con override manuale documentato.
Prima del fix `compliant + ≥2 evidenze valide` restituiva 5, gonfiando il
self-assessment rispetto a un assessment ENX reale.
"""
import datetime
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def env(db):
    from apps.controls.models import Control, ControlInstance, Framework
    from apps.documents.models import Evidence
    from apps.plants.models import Plant, PlantFramework

    user = User.objects.create_user(username="mat_user", email="mat@test.com", password="test")
    plant = Plant.objects.create(
        code="MAT-P", name="Plant Maturity", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )
    fw = Framework.objects.create(
        code="TISAX_L3", name="TISAX L3", version="6.0",
        published_at=timezone.localdate(),
    )
    PlantFramework.objects.create(
        plant=plant, framework=fw,
        active_from=timezone.localdate(), level="L3", active=True,
    )

    counter = {"n": 0}

    def make_instance(status, valid_evidences=0):
        counter["n"] += 1
        n = counter["n"]
        control = Control.objects.create(
            framework=fw, external_id=f"MAT-{n}",
            translations={"it": {"title": f"Controllo {n}"}},
            evidence_requirement={},
        )
        inst = ControlInstance.objects.create(
            plant=plant, control=control, status=status, created_by=user,
        )
        future = timezone.localdate() + datetime.timedelta(days=365)
        for i in range(valid_evidences):
            ev = Evidence.objects.create(
                title=f"Ev {n}-{i}", evidence_type="report",
                valid_until=future, plant=plant, created_by=user,
            )
            inst.evidences.add(ev)
        return inst

    return make_instance


@pytest.mark.django_db
@pytest.mark.parametrize("status,evidences,expected", [
    ("non_valutato", 0, 0),
    ("na", 0, 0),
    ("gap", 0, 1),
    ("parziale", 0, 2),
    ("parziale", 2, 2),          # parziale resta 2 indipendentemente dalle evidenze
    ("compliant", 0, 3),         # definito e documentato
    ("compliant", 1, 3),         # serve ≥2 per salire a 4
    ("compliant", 2, 4),         # gestito e misurato — cap auto al 4
    ("compliant", 5, 4),         # mai 5 in automatico
])
def test_calc_maturity_capped_at_4(env, status, evidences, expected):
    inst = env(status, valid_evidences=evidences)
    assert inst.calc_maturity_level == expected


@pytest.mark.django_db
def test_maturity_5_only_via_documented_override(env):
    """Il 5 si raggiunge solo con override manuale documentato."""
    inst = env("compliant", valid_evidences=2)
    assert inst.calc_maturity_level == 4

    inst.maturity_level = 5
    inst.maturity_level_override = True
    inst.save(update_fields=["maturity_level", "maturity_level_override"])
    inst.refresh_from_db()
    assert inst.calc_maturity_level == 5
