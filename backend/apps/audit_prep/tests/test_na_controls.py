"""
Controlli non applicabili nell'audit prep.

Mettere un controllo in N/A è una decisione governata: richiede giustificazione
scritta e doppio approvatore. L'auto-validazione la trattava come una mancanza e
apriva una non conformità minore — cioè trasformava una decisione motivata nel
suo contrario.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    u = User.objects.create_user(username="na_u", email="na@test.com", password="x")
    UserPlantAccess.objects.create(
        user=u, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org"
    )
    return u


@pytest.fixture
def plant(db):
    from apps.plants.models import Plant
    return Plant.objects.create(
        code="NA-P", name="Plant NA", country="IT",
        nis2_scope="non_soggetto", status="attivo",
    )


@pytest.fixture
def framework(db):
    from apps.controls.models import Framework
    return Framework.objects.create(
        code="TISAX-NA", name="TISAX prototipi", version="6.0",
        published_at=timezone.localdate(),
    )


def _control(framework, external_id):
    from apps.controls.models import Control
    return Control.objects.create(
        framework=framework, external_id=external_id,
        translations={"it": {"title": f"Controllo {external_id}"}},
        evidence_requirement={},
    )


def _instance(plant, framework, external_id, **kw):
    from apps.controls.models import ControlInstance
    return ControlInstance.objects.create(
        plant=plant, control=_control(framework, external_id), **kw
    )


@pytest.fixture
def prep(db, plant, framework, user):
    from apps.audit_prep.models import AuditPrep
    return AuditPrep.objects.create(
        plant=plant, framework=framework, title="Audit prototipi",
        audit_date=timezone.localdate(), status="in_corso", created_by=user,
    )


def _item(prep, ci, user, status="mancante"):
    from apps.audit_prep.models import EvidenceItem
    return EvidenceItem.objects.create(
        audit_prep=prep, control_instance=ci,
        description=f"{ci.control.external_id} — evidenza",
        status=status, created_by=user,
    )


# ── Valutazione ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_na_control_is_not_a_missing_evidence(prep, plant, framework, user):
    """Il caso segnalato: protezione prototipi dichiarata N/A da chi prototipi
    non ne tratta, e il sistema apriva cinque non conformità."""
    from apps.audit_prep.models import AuditFinding, EvidenceItem
    from apps.audit_prep.validation import auto_validate_prep

    ci = _instance(
        plant, framework, "ISA-8.4.1", status="na",
        na_justification="Lo stabilimento non tratta prototipi di clienti.",
    )
    item = _item(prep, ci, user)

    result = auto_validate_prep(prep, user)

    item.refresh_from_db()
    assert item.status == "na"
    assert result["na"] == 1
    assert result["mancante"] == 0
    assert result["findings_created"] == 0
    assert not AuditFinding.objects.filter(audit_prep=prep).exists()
    assert EvidenceItem.objects.filter(audit_prep=prep, status="mancante").count() == 0


@pytest.mark.django_db
def test_the_justification_is_carried_into_the_notes(prep, plant, framework, user):
    """L'auditor deve poter leggere PERCHÉ è escluso, senza uscire dal prep."""
    from apps.audit_prep.validation import auto_validate_prep

    ci = _instance(
        plant, framework, "ISA-8.4.2", status="na",
        na_justification="Nessun prototipo fisico presente in stabilimento.",
        na_review_by=timezone.localdate(),
    )
    item = _item(prep, ci, user)
    auto_validate_prep(prep, user)

    item.refresh_from_db()
    assert "Nessun prototipo fisico" in item.notes
    assert "riesaminare" in item.notes.lower()


@pytest.mark.django_db
def test_soa_excluded_control_is_treated_the_same(prep, plant, framework, user):
    """Anche l'esclusione dalla SoA è una decisione motivata, non una lacuna."""
    from apps.audit_prep.models import AuditFinding
    from apps.audit_prep.validation import auto_validate_prep

    ci = _instance(
        plant, framework, "ISA-8.5.1", status="non_valutato",
        applicability="escluso",
        exclusion_justification="Attività non svolta dall'organizzazione.",
    )
    item = _item(prep, ci, user)
    auto_validate_prep(prep, user)

    item.refresh_from_db()
    assert item.status == "na"
    assert not AuditFinding.objects.filter(audit_prep=prep).exists()


@pytest.mark.django_db
def test_an_applicable_control_without_evidence_is_still_a_finding(prep, plant, framework, user):
    """La correzione non deve rendere indulgente il resto della validazione."""
    from apps.audit_prep.models import AuditFinding
    from apps.audit_prep.validation import auto_validate_prep

    ci = _instance(plant, framework, "ISA-1.1.1", status="gap")
    _item(prep, ci, user)
    result = auto_validate_prep(prep, user)

    assert result["mancante"] == 1
    assert result["findings_created"] == 1
    assert AuditFinding.objects.filter(
        audit_prep=prep, finding_type="minor_nc"
    ).exists()


# ── Rilievi già aperti ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_a_previous_finding_is_reported_not_closed(prep, plant, framework, user):
    """Un rilievo aperto quando il controllo era ancora applicabile non ha più
    oggetto: viene contato e lasciato all'auditor. Chiuderlo d'ufficio
    richiederebbe un'evidenza di chiusura che non esiste, e cancellerebbe un
    record che l'auditor potrebbe aver già visto."""
    from apps.audit_prep.models import AuditFinding
    from apps.audit_prep.validation import auto_validate_prep

    ci = _instance(
        plant, framework, "ISA-8.4.3", status="na",
        na_justification="Attività non applicabile a questo sito.",
    )
    _item(prep, ci, user)
    finding = AuditFinding.objects.create(
        audit_prep=prep, control_instance=ci, finding_type="minor_nc",
        title="Evidenza mancante — ISA-8.4.3", description="Generato prima",
        status="open", auto_generated=True, created_by=user,
        audit_date=timezone.localdate(),
    )

    result = auto_validate_prep(prep, user)

    assert result["findings_obsolete"] == 1
    finding.refresh_from_db()
    assert finding.status == "open", "il rilievo resta all'auditor"


# ── Prontezza ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_readiness_ignores_non_applicable_items(prep, plant, framework, user):
    """Le voci N/A escono da numeratore e denominatore: non c'è nulla da
    preparare, quindi non spostano la prontezza né in su né in giù."""
    from apps.audit_prep.services import calc_readiness_score

    _item(prep, _instance(plant, framework, "C.1"), user, status="presente")
    _item(prep, _instance(plant, framework, "C.2"), user, status="mancante")
    assert calc_readiness_score(prep) == 50

    _item(prep, _instance(plant, framework, "C.3"), user, status="na")
    _item(prep, _instance(plant, framework, "C.4"), user, status="na")
    assert calc_readiness_score(prep) == 50, "il punteggio non deve cambiare"


# ── Popolamento ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_seeding_marks_non_applicable_controls_from_the_start(prep, plant, framework, user):
    """Senza questo, le voci nascono `mancante` e restano tali finché qualcuno
    non lancia l'auto-validazione."""
    from apps.audit_prep.models import EvidenceItem
    from apps.audit_prep.services import seed_evidence_items_for_prep

    _instance(plant, framework, "ISA-8.4.1", status="na",
              na_justification="Non applicabile.")
    _instance(plant, framework, "ISA-1.1.1", status="gap")

    seed_evidence_items_for_prep(
        prep, ["TISAX-NA"], coverage_type="full", user=user
    )

    statuses = dict(
        EvidenceItem.objects.filter(audit_prep=prep).values_list(
            "control_instance__control__external_id", "status"
        )
    )
    assert statuses["ISA-8.4.1"] == "na"
    assert statuses["ISA-1.1.1"] == "mancante"


@pytest.mark.django_db
def test_sampling_does_not_spend_slots_on_non_applicable_controls(prep, plant, framework, user):
    """In un audit a campione gli slot vanno ai controlli da verificare
    davvero: le esclusioni restano in elenco ma fuori dal campione."""
    from apps.audit_prep.models import EvidenceItem
    from apps.audit_prep.services import seed_evidence_items_for_prep

    for n in range(20):
        _instance(plant, framework, f"AP.{n}", status="non_valutato")
    for n in range(6):
        _instance(plant, framework, f"NA.{n}", status="na",
                  na_justification="Non applicabile a questo sito.")

    seed_evidence_items_for_prep(
        prep, ["TISAX-NA"], coverage_type="campione", user=user
    )

    items = EvidenceItem.objects.filter(audit_prep=prep)
    applicable = items.exclude(status="na").count()
    # Il campione è ~25% dei soli 20 controlli applicabili, non dei 26 totali.
    assert applicable >= 5
    assert items.filter(status="na").count() == 6, "le esclusioni restano in elenco"
