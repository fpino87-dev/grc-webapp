"""
Test C4 — propagazione coerente col modello evidence-based.

La propagazione opera **solo entro lo stesso plant** (la propagazione
cross-plant è stata rimossa: ogni sito deve avere evidenze e controlli propri,
altrimenti la conformità non è credibile in audit). Nello stesso plant la
propagazione di 'compliant' collega le evidenze del controllo sorgente al
target, così il controllo equivalente non risulta conforme con evidenze vuote.
"""
import datetime
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def env(db):
    from apps.controls.models import Control, ControlInstance, ControlMapping, Framework
    from apps.documents.models import Evidence
    from apps.plants.models import Plant

    user = User.objects.create_user(username="prop_user", email="prop@test.com", password="test")
    fw = Framework.objects.create(
        code="ISO-PROP", name="ISO Prop", version="2022", published_at=timezone.localdate(),
    )
    # Due controlli mappati come equivalenti (propagabile bidirezionale)
    ctrl_a = Control.objects.create(
        framework=fw, external_id="A-1", translations={"it": {"title": "A1"}}, evidence_requirement={},
    )
    ctrl_b = Control.objects.create(
        framework=fw, external_id="B-1", translations={"it": {"title": "B1"}}, evidence_requirement={},
    )
    ControlMapping.objects.create(source_control=ctrl_a, target_control=ctrl_b, relationship="equivalente")

    plant_p = Plant.objects.create(code="P-P", name="Plant P", country="IT", nis2_scope="non_soggetto", status="attivo")
    plant_q = Plant.objects.create(code="P-Q", name="Plant Q", country="IT", nis2_scope="non_soggetto", status="attivo")

    def make(plant, control, status):
        return ControlInstance.objects.create(plant=plant, control=control, status=status, created_by=user)

    def evidence(plant):
        future = timezone.localdate() + datetime.timedelta(days=365)
        return Evidence.objects.create(
            title="Ev", evidence_type="report", valid_until=future, plant=plant, created_by=user,
        )

    return {"user": user, "ctrl_a": ctrl_a, "ctrl_b": ctrl_b,
            "plant_p": plant_p, "plant_q": plant_q, "make": make, "evidence": evidence}


@pytest.mark.django_db
def test_never_touches_other_plants(env):
    """La propagazione non raggiunge mai un altro plant: il target su Q resta invariato."""
    from apps.controls.services import propagate_control

    src = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    src.evidences.add(env["evidence"](env["plant_p"]))
    tgt_q = env["make"](env["plant_q"], env["ctrl_b"], "non_valutato")

    res = propagate_control(src, env["user"])
    assert res["propagated_to"] == 0  # nessun target nello stesso plant

    tgt_q.refresh_from_db()
    assert tgt_q.status == "non_valutato"


@pytest.mark.django_db
def test_compliant_same_plant_copies_evidence(env):
    """Compliant same-plant: il target diventa compliant e eredita le evidenze."""
    from apps.controls.services import propagate_control

    src = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    ev = env["evidence"](env["plant_p"])
    src.evidences.add(ev)
    tgt = env["make"](env["plant_p"], env["ctrl_b"], "non_valutato")

    res = propagate_control(src, env["user"])
    assert res["propagated_to"] == 1

    tgt.refresh_from_db()
    assert tgt.status == "compliant"
    assert ev in tgt.evidences.all()  # niente compliant con evidenze vuote


@pytest.mark.django_db
def test_na_propagates_same_plant_only(env):
    """N/A si propaga nello stesso plant ma non verso altri plant."""
    from apps.controls.services import propagate_control

    src = env["make"](env["plant_p"], env["ctrl_a"], "na")
    src.na_justification = "Controllo non applicabile a questo perimetro produttivo."
    src.save(update_fields=["na_justification"])
    tgt_p = env["make"](env["plant_p"], env["ctrl_b"], "non_valutato")
    tgt_q = env["make"](env["plant_q"], env["ctrl_b"], "non_valutato")

    res = propagate_control(src, env["user"])
    assert res["propagated_to"] == 1

    tgt_p.refresh_from_db()
    tgt_q.refresh_from_db()
    assert tgt_p.status == "na"
    assert tgt_p.na_justification
    assert tgt_q.status == "non_valutato"  # altro plant: invariato


# ── can_propagate (serializer) — il pulsante "⇒ propaga" appare solo se utile ──

def _can_propagate(instance):
    """Serializza l'istanza come fa la lista e legge il flag."""
    from apps.controls.serializers import ControlInstanceSerializer
    from apps.controls.views.instances import ControlInstanceViewSet

    obj = ControlInstanceViewSet.queryset.get(pk=instance.pk)
    return ControlInstanceSerializer(obj, context={}).data["can_propagate"]


@pytest.mark.django_db
def test_can_propagate_true_with_equivalent_target_in_plant(env):
    src = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    env["make"](env["plant_p"], env["ctrl_b"], "non_valutato")
    assert _can_propagate(src) is True


@pytest.mark.django_db
def test_can_propagate_false_without_target_instance_in_plant(env):
    """Il mapping esiste, ma il controllo equivalente non è istanziato in
    questo sito (es. framework non assegnato): il pulsante non deve apparire."""
    src = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    env["make"](env["plant_q"], env["ctrl_b"], "non_valutato")  # solo sull'altro sito
    assert _can_propagate(src) is False


@pytest.mark.django_db
def test_can_propagate_false_for_non_propagable_status(env):
    src = env["make"](env["plant_p"], env["ctrl_a"], "gap")
    env["make"](env["plant_p"], env["ctrl_b"], "non_valutato")
    assert _can_propagate(src) is False


@pytest.mark.django_db
def test_can_propagate_respects_covers_direction(env):
    """'covers' propaga solo source→target: il covered (B) non deve mostrare
    il pulsante verso chi lo copre (A)."""
    from apps.controls.models import ControlMapping

    ControlMapping.objects.filter(source_control=env["ctrl_a"]).update(relationship="covers")
    inst_b = env["make"](env["plant_p"], env["ctrl_b"], "compliant")
    inst_a = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    assert _can_propagate(inst_b) is False  # B è il covered: direzione sbagliata
    assert _can_propagate(inst_a) is True   # A copre B: direzione giusta


@pytest.mark.django_db
def test_can_propagate_ignores_non_propagable_relationships(env):
    """parziale/correlato (la massa del crosswalk C12) non rendono il pulsante visibile."""
    from apps.controls.models import ControlMapping

    ControlMapping.objects.filter(source_control=env["ctrl_a"]).update(relationship="parziale")
    src = env["make"](env["plant_p"], env["ctrl_a"], "compliant")
    env["make"](env["plant_p"], env["ctrl_b"], "non_valutato")
    assert _can_propagate(src) is False
