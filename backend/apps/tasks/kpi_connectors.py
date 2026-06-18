"""
Connettori KPI interni (source="internal").

Calcolano il valore di un KPI operativo direttamente dai dati dei moduli GRC
(M03/M04/M07/M09/M11/M14/M15/M17), senza ingest esterno via API. Sostituiscono
il push manuale per tutti i KPI il cui dato vive già dentro la piattaforma.

Ogni connettore ha firma ``(plant, week_start) -> dict`` con ritorno
``{"value": float|None, "run_count": int, "note": str}``, identico a quello di
``services.calculate_kpi_value``: così ``compute_and_store_kpi_snapshot`` tratta
checklist e connettori interni in modo uniforme. ``run_count`` riporta la
dimensione del campione (denominatore) usata per il calcolo.

Convenzioni:
- ``plant`` è sempre un'istanza Plant concreta quando il task espande i KPI
  globali su tutti i plant attivi; se ``None`` il connettore aggrega su tutti.
- I KPI di stato puntuale (conteggi/rate sullo stato corrente) sono misurati
  "as of" il momento di esecuzione e archiviati sulla settimana ``week_start``.
- I KPI di periodo (incidenti) filtrano sulla finestra [week_start, +6 giorni];
  se nel periodo non c'è alcun campione ritornano ``no_data`` (mai un falso 0).
"""

import datetime

from django.db.models import Q
from django.utils import timezone


def _no_data(note: str) -> dict:
    return {"value": None, "run_count": 0, "note": note}


def _result(value, sample: int, note: str) -> dict:
    return {"value": value, "run_count": sample, "note": note}


def _rate(num: int, denom: int) -> float:
    return round(num / denom * 100, 2)


def _week_range(week_start: datetime.date):
    return week_start, week_start + datetime.timedelta(days=6)


# ── M03 Controlli ────────────────────────────────────────────────────────────
def controls_compliance_rate(plant, week_start) -> dict:
    """% di controlli applicabili in stato 'compliant' (stato puntuale)."""
    from apps.controls.models import ControlInstance

    qs = ControlInstance.objects.filter(applicability="applicabile").exclude(status="na")
    if plant is not None:
        qs = qs.filter(plant=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun controllo applicabile.")
    compliant = qs.filter(status="compliant").count()
    return _result(_rate(compliant, total), total, f"{compliant}/{total} controlli compliant")


# ── M07 Documenti/Evidenze ────────────────────────────────────────────────────
def evidence_expiry_rate(plant, week_start) -> dict:
    """% di evidenze ancora valide (valid_until assente o futuro)."""
    from apps.documents.models import Evidence

    today = timezone.localdate()
    qs = Evidence.objects.all()
    if plant is not None:
        qs = qs.filter(plant=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessuna evidenza registrata.")
    valid = qs.filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).count()
    return _result(_rate(valid, total), total, f"{valid}/{total} evidenze valide")


# ── M11 PDCA ──────────────────────────────────────────────────────────────────
def open_pdca_over_90days(plant, week_start) -> dict:
    """N. cicli PDCA aperti da oltre 90 giorni (stato puntuale)."""
    from apps.pdca.models import PdcaCycle

    cutoff = timezone.now() - datetime.timedelta(days=90)
    qs = (
        PdcaCycle.objects.filter(closed_at__isnull=True)
        .exclude(fase_corrente__in=["chiuso", "archiviato"])
        .filter(created_at__lte=cutoff)
    )
    if plant is not None:
        qs = qs.filter(plant=plant)
    n = qs.count()
    return _result(float(n), n, f"{n} cicli PDCA aperti da oltre 90 giorni")


# ── M17 Audit Readiness ─────────────────────────────────────────────────────--
def audit_findings_open_rate(plant, week_start) -> dict:
    """% di finding di audit ancora aperti sul totale registrato."""
    from apps.audit_prep.models import AuditFinding

    qs = AuditFinding.objects.all()
    if plant is not None:
        qs = qs.filter(audit_prep__plant=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun finding di audit registrato.")
    open_n = qs.exclude(status__in=["closed", "accepted_by_auditor"]).count()
    return _result(_rate(open_n, total), total, f"{open_n}/{total} finding aperti")


# ── M15 Training ───────────────────────────────────────────────────────────---
def training_completion_rate(plant, week_start) -> dict:
    """% di iscrizioni a corsi obbligatori attivi in stato 'completato'."""
    from apps.training.models import TrainingEnrollment

    qs = TrainingEnrollment.objects.filter(course__mandatory=True, course__status="attivo")
    if plant is not None:
        qs = qs.filter(course__plants=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessuna iscrizione a formazione obbligatoria.")
    completed = qs.filter(status="completato").count()
    return _result(_rate(completed, total), total, f"{completed}/{total} completati")


# ── M04 Asset IT ───────────────────────────────────────────────────────────---
def systems_eol_count(plant, week_start) -> dict:
    """N. di asset IT con eol_date già trascorsa (stato puntuale)."""
    from apps.assets.models import AssetIT

    today = timezone.localdate()
    qs = AssetIT.objects.filter(eol_date__isnull=False, eol_date__lt=today)
    if plant is not None:
        qs = qs.filter(plant=plant)
    n = qs.count()
    return _result(float(n), n, f"{n} sistemi IT a fine vita")


# ── M09 Incidenti ──────────────────────────────────────────────────────────---
def incident_mttr_hours(plant, week_start) -> dict:
    """Ore medie detected_at→closed_at per gli incidenti chiusi nella settimana."""
    from apps.incidents.models import Incident

    start, end = _week_range(week_start)
    qs = Incident.objects.filter(
        status="chiuso",
        closed_at__isnull=False,
        closed_at__date__gte=start,
        closed_at__date__lte=end,
    )
    if plant is not None:
        qs = qs.filter(plant=plant)

    durations = []
    for inc in qs.only("detected_at", "closed_at"):
        if inc.detected_at and inc.closed_at and inc.closed_at >= inc.detected_at:
            durations.append((inc.closed_at - inc.detected_at).total_seconds() / 3600)
    if not durations:
        return _no_data("Nessun incidente chiuso nel periodo.")
    avg = sum(durations) / len(durations)
    return _result(round(avg, 2), len(durations), f"Media su {len(durations)} incidenti chiusi")


def incident_recurrence_rate(plant, week_start) -> dict:
    """% di incidenti ricorrenti sul totale rilevato nella settimana."""
    from apps.incidents.models import Incident

    start, end = _week_range(week_start)
    qs = Incident.objects.filter(detected_at__date__gte=start, detected_at__date__lte=end)
    if plant is not None:
        qs = qs.filter(plant=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun incidente nel periodo.")
    recurrent = qs.filter(is_recurrent=True).count()
    return _result(_rate(recurrent, total), total, f"{recurrent}/{total} ricorrenti")


def incident_rca_completion_rate(plant, week_start) -> dict:
    """% di incidenti significativi (rilevati nel periodo) con RCA approvata."""
    from apps.incidents.models import Incident

    start, end = _week_range(week_start)
    qs = Incident.objects.filter(
        is_significant=True, detected_at__date__gte=start, detected_at__date__lte=end
    )
    if plant is not None:
        qs = qs.filter(plant=plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun incidente significativo nel periodo.")
    with_rca = qs.filter(rca__isnull=False, rca__approved_at__isnull=False).count()
    return _result(_rate(with_rca, total), total, f"{with_rca}/{total} con RCA approvata")


# ── M14 Fornitori ──────────────────────────────────────────────────────────---
def _critical_suppliers(plant):
    """Fornitori attivi considerati critici: risk_level=critico o nis2_relevant."""
    from apps.suppliers.models import Supplier

    qs = Supplier.objects.filter(status="attivo").filter(
        Q(risk_level="critico") | Q(nis2_relevant=True)
    )
    if plant is not None:
        qs = qs.filter(plants=plant)
    return qs.distinct()


def _valid_assessment_q(today):
    """Assessment completato/approvato e non scaduto (next_assessment_date)."""
    return Q(assessments__status__in=["completato", "approvato"]) & (
        Q(assessments__next_assessment_date__isnull=True)
        | Q(assessments__next_assessment_date__gte=today)
    )


def suppliers_assessed_rate(plant, week_start) -> dict:
    """% di fornitori critici con valutazione di sicurezza valida."""
    today = timezone.localdate()
    total = _critical_suppliers(plant).count()
    if total == 0:
        return _no_data("Nessun fornitore critico.")
    assessed = _critical_suppliers(plant).filter(_valid_assessment_q(today)).distinct().count()
    return _result(_rate(assessed, total), total, f"{assessed}/{total} fornitori valutati")


def suppliers_critical_unassessed(plant, week_start) -> dict:
    """N. di fornitori critici privi di valutazione valida (stato puntuale)."""
    today = timezone.localdate()
    total = _critical_suppliers(plant).count()
    assessed = _critical_suppliers(plant).filter(_valid_assessment_q(today)).distinct().count()
    unassessed = total - assessed
    return _result(float(unassessed), total, f"{unassessed}/{total} fornitori critici non valutati")


# Registry kpi_code → connettore. I codici qui presenti DEVONO avere
# source="internal" nel catalogo (kpi_catalog) e nelle KPIDefinition salvate.
INTERNAL_CONNECTORS = {
    "controls_compliance_rate": controls_compliance_rate,
    "evidence_expiry_rate": evidence_expiry_rate,
    "open_pdca_over_90days": open_pdca_over_90days,
    "audit_findings_open_rate": audit_findings_open_rate,
    "training_completion_rate": training_completion_rate,
    "systems_eol_count": systems_eol_count,
    "incident_mttr_hours": incident_mttr_hours,
    "incident_recurrence_rate": incident_recurrence_rate,
    "incident_rca_completion_rate": incident_rca_completion_rate,
    "suppliers_assessed_rate": suppliers_assessed_rate,
    "suppliers_critical_unassessed": suppliers_critical_unassessed,
}


def compute_internal_kpi(kpi_def, plant, week_start) -> dict:
    """
    Dispatcher: invoca il connettore registrato per kpi_def.kpi_code.
    Se non esiste un connettore per quel codice ritorna no_data (un KPI
    source=internal senza connettore non è popolabile e va segnalato).
    """
    connector = INTERNAL_CONNECTORS.get(kpi_def.kpi_code)
    if connector is None:
        return _no_data(
            f"Nessun connettore interno per '{kpi_def.kpi_code}'."
        )
    return connector(plant, week_start)
