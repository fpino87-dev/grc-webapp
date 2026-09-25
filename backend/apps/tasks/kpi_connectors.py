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
    open_n = qs.exclude(status__in=["closed", "accepted_by_auditor", "not_pursued"]).count()
    return _result(_rate(open_n, total), total, f"{open_n}/{total} finding aperti")


# ── M15 Training ───────────────────────────────────────────────────────────---
# Formazione a evidenze: i numeri vengono dalle erogazioni registrate con prova
# e dai gruppi destinatari (conteggi), non dalle iscrizioni per persona.
def training_completion_rate(plant, week_start) -> dict:
    """% di personale coperto dalla formazione obbligatoria del piano
    dell'anno (erogazioni valide / headcount dei gruppi destinatari)."""
    from apps.training.services import training_coverage

    cov = training_coverage(plant)
    if not cov["target"]:
        return _no_data("Nessun corso obbligatorio a piano con gruppi destinatari.")
    return _result(cov["pct"], cov["target"],
                   f"{cov['covered']}/{cov['target']} persone formate")


def training_plan_progress(plant, week_start) -> dict:
    """% di voci del piano dell'anno, già scadute, con un'erogazione registrata."""
    from apps.training.services import plan_progress

    prog = plan_progress(plant)
    if not prog["due"]:
        return _no_data("Nessuna voce del piano ancora scaduta.")
    return _result(prog["pct"], prog["due"], f"{prog['done']}/{prog['due']} voci svolte")


def training_plan_overdue(plant, week_start) -> dict:
    """N. di voci del piano scadute senza erogazione (stato puntuale)."""
    from apps.training.services import plan_progress

    n = plan_progress(plant)["overdue"]
    return _result(float(n), n, f"{n} voci del piano in ritardo")


def _latest_phishing(plant):
    from apps.training.services import latest_phishing

    return latest_phishing(plant)


_NO_PHISHING = "Nessuna simulazione di phishing negli ultimi 12 mesi."


def phishing_click_rate(plant, week_start) -> dict:
    """% di clic sull'ultima simulazione di phishing di ogni sito (12 mesi)."""
    ph = _latest_phishing(plant)
    if not ph["sent"]:
        return _no_data(_NO_PHISHING)
    return _result(ph["click_pct"], ph["sent"], f"{ph['clicked']}/{ph['sent']} clic")


def phishing_report_rate(plant, week_start) -> dict:
    """% di segnalazioni sull'ultima simulazione di phishing di ogni sito (12 mesi)."""
    ph = _latest_phishing(plant)
    if not ph["sent"]:
        return _no_data(_NO_PHISHING)
    return _result(ph["report_pct"], ph["sent"], f"{ph['reported']}/{ph['sent']} segnalazioni")


def board_training_valid(plant, week_start) -> dict:
    """% di componenti in carica dell'organo di gestione con formazione valida
    (NIS2 art. 20). La nota riporta solo conteggi, nessun nominativo."""
    from apps.training.services import board_training

    board = board_training(plant)
    if not board["total"]:
        return _no_data("Nessun componente in carica di un organo di gestione (CdA).")
    return _result(board["pct"], board["total"],
                   f"{board['trained']}/{board['total']} componenti con formazione valida")


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


# ── M16 BCP / Disaster Recovery ─────────────────────────────────────────────
# I test di continuità sono eventi rari (tipicamente annuali): misurarne la
# "quantità nella settimana" darebbe 51 settimane vuote e una piena. Si misura
# quindi lo STATO — anzianità dell'ultimo test, esito, scostamento dagli
# obiettivi — che è leggibile ogni settimana e disegna un trend sensato.

DR_WINDOW_DAYS = 365  # finestra mobile per gli indicatori "negli ultimi 12 mesi"


def _active_bcp_plans(plant):
    """Piani BCP approvati: le bozze non sono impegni e gli archiviati non valgono più."""
    from apps.bcp.models import BcpPlan

    qs = BcpPlan.objects.filter(status="approvato")
    if plant is not None:
        qs = qs.filter(plant=plant)
    return qs


def _recent_bcp_tests(plant, today):
    """Test eseguiti nella finestra mobile, sui soli piani attivi."""
    from apps.bcp.models import BcpTest

    return BcpTest.objects.filter(
        plan__in=_active_bcp_plans(plant),
        test_date__gte=today - datetime.timedelta(days=DR_WINDOW_DAYS),
        test_date__lte=today,
    )


def dr_test_age_days(plant, week_start) -> dict:
    """Giorni dall'ultimo test DR del piano messo peggio (stato puntuale).

    Si prende il piano con l'attesa più lunga, non la media: un solo piano
    critico mai provato non deve essere mascherato dagli altri in regola. Un
    piano mai testato conta dalla propria creazione, così non sparisce dal
    conteggio proprio perché non è mai stato provato.
    """
    today = timezone.localdate()
    plans = list(_active_bcp_plans(plant).values("id", "title", "last_test_date", "created_at"))
    if not plans:
        return _no_data("Nessun piano BCP approvato.")

    worst_age, worst_title, never_tested = -1, "", 0
    for plan in plans:
        base = plan["last_test_date"] or timezone.localtime(plan["created_at"]).date()
        if plan["last_test_date"] is None:
            never_tested += 1
        age = (today - base).days
        if age > worst_age:
            worst_age, worst_title = age, plan["title"]

    note = f"{worst_age} giorni dall'ultimo test di «{worst_title}»"
    if never_tested:
        note += f" — {never_tested}/{len(plans)} piani mai testati"
    return _result(float(worst_age), len(plans), note)


def dr_test_pass_rate(plant, week_start) -> dict:
    """% di test DR con esito superato negli ultimi 12 mesi.

    Un test "parziale" non conta come superato: la continuità o è dimostrata
    o non lo è.
    """
    today = timezone.localdate()
    tests = _recent_bcp_tests(plant, today)
    total = tests.count()
    if total == 0:
        return _no_data("Nessun test DR negli ultimi 12 mesi.")
    passed = tests.filter(result="superato").count()
    return _result(_rate(passed, total), total, f"{passed}/{total} test superati")


def dr_rto_gap_hours(plant, week_start) -> dict:
    """Scostamento medio fra RTO ottenuto nei test e RTO obiettivo del piano.

    Positivo = il ripristino ha richiesto più tempo di quanto il piano prometta.
    È la misura che un auditor chiede per prima: un piano con RTO dichiarato di
    4 ore, provato in 30, non è un piano.
    """
    today = timezone.localdate()
    tests = _recent_bcp_tests(plant, today).filter(
        rto_achieved_hours__isnull=False, plan__rto_hours__isnull=False
    ).select_related("plan")
    gaps = [t.rto_achieved_hours - t.plan.rto_hours for t in tests]
    if not gaps:
        return _no_data("Nessun test DR con RTO misurato negli ultimi 12 mesi.")
    avg_gap = round(sum(gaps) / len(gaps), 2)
    worst = max(gaps)
    return _result(
        float(avg_gap),
        len(gaps),
        f"Scostamento medio {avg_gap}h su {len(gaps)} test (peggiore {worst}h)",
    )


def dr_plans_overdue_count(plant, week_start) -> dict:
    """N. di piani BCP con test scaduto o mai eseguito (stato puntuale)."""
    today = timezone.localdate()
    plans = _active_bcp_plans(plant)
    total = plans.count()
    if total == 0:
        return _no_data("Nessun piano BCP approvato.")
    overdue = plans.filter(
        Q(next_test_date__lt=today) | Q(last_test_date__isnull=True)
    ).count()
    return _result(float(overdue), total, f"{overdue}/{total} piani con test scaduto o mai eseguito")


def bcp_critical_process_coverage(plant, week_start) -> dict:
    """% di processi critici della BIA coperti da almeno un piano BCP approvato.

    Scopre i processi scoperti: è il buco che in audit costa di più, perché
    non si vede da nessuna parte finché non serve il piano.
    """
    from apps.bia.models import CriticalProcess

    processes = CriticalProcess.objects.filter(status__in=["validato", "approvato"])
    if plant is not None:
        processes = processes.filter(plant=plant)
    total = processes.count()
    if total == 0:
        return _no_data("Nessun processo critico validato in BIA.")

    plans = _active_bcp_plans(plant)
    covered = processes.filter(
        Q(id__in=plans.values("critical_processes"))
        | Q(id__in=plans.exclude(critical_process__isnull=True).values("critical_process"))
    ).distinct().count()
    return _result(_rate(covered, total), total, f"{covered}/{total} processi critici coperti")


def bcp_rto_meets_bia_target_rate(plant, week_start) -> dict:
    """% di piani BCP il cui RTO dichiarato rispetta il target della BIA.

    Un piano può essere approvato e testato e promettere comunque MENO di
    quanto il processo richiede: qui il confronto è con il target più
    stringente fra i processi che il piano copre.
    """
    plans = _active_bcp_plans(plant).filter(rto_hours__isnull=False).prefetch_related(
        "critical_processes"
    ).select_related("critical_process")

    checked, compliant = 0, 0
    for plan in plans:
        targets = [
            p.rto_target_hours
            for p in list(plan.critical_processes.all()) + ([plan.critical_process] if plan.critical_process else [])
            if p is not None and p.rto_target_hours is not None
        ]
        if not targets:
            continue
        checked += 1
        if plan.rto_hours <= min(targets):
            compliant += 1

    if checked == 0:
        return _no_data("Nessun piano BCP collegato a un processo con RTO target.")
    return _result(_rate(compliant, checked), checked, f"{compliant}/{checked} piani entro il target BIA")


# ── M04 Manutenzione impianti e apparati ─────────────────────────────────────


def _maintained_assets(plant):
    """Asset con una manutenzione programmata: gli altri non sono in ritardo,
    semplicemente non hanno un piano e non vanno conteggiati."""
    from apps.assets.models import Asset

    qs = Asset.objects.filter(maintenance_frequency_months__isnull=False)
    if plant is not None:
        qs = qs.filter(plant=plant)
    return qs


def maintenance_plan_compliance_rate(plant, week_start) -> dict:
    """% di asset con manutenzione programmata entro la scadenza (stato puntuale)."""
    today = timezone.localdate()
    qs = _maintained_assets(plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun asset con manutenzione programmata.")
    in_time = qs.filter(next_maintenance_date__gte=today).count()
    return _result(_rate(in_time, total), total, f"{in_time}/{total} asset entro la scadenza")


def maintenance_overdue_count(plant, week_start) -> dict:
    """N. di asset con manutenzione scaduta (stato puntuale)."""
    today = timezone.localdate()
    qs = _maintained_assets(plant)
    total = qs.count()
    if total == 0:
        return _no_data("Nessun asset con manutenzione programmata.")
    overdue = qs.filter(next_maintenance_date__lt=today).count()
    return _result(float(overdue), total, f"{overdue}/{total} manutenzioni scadute")


def facility_check_age_days(plant, week_start) -> dict:
    """Giorni dall'ultima verifica dell'impianto messo peggio.

    Vale per gli impianti di supporto (UPS, gruppi elettrogeni, antincendio,
    climatizzazione, sicurezza fisica): come per i test DR si prende il caso
    peggiore, perché è quello che si rompe quando serve. Un impianto mai
    verificato conta dalla data di installazione, o dalla registrazione se
    l'installazione non è nota.
    """
    from apps.assets.models import AssetFacility

    today = timezone.localdate()
    qs = AssetFacility.objects.all()
    if plant is not None:
        qs = qs.filter(plant=plant)
    facilities = list(qs.values("name", "last_maintenance_date", "installation_date", "created_at"))
    if not facilities:
        return _no_data("Nessun impianto censito.")

    worst_age, worst_name, never = -1, "", 0
    for f in facilities:
        base = (
            f["last_maintenance_date"]
            or f["installation_date"]
            or timezone.localtime(f["created_at"]).date()
        )
        if f["last_maintenance_date"] is None:
            never += 1
        age = (today - base).days
        if age > worst_age:
            worst_age, worst_name = age, f["name"]

    note = f"{worst_age} giorni dall'ultima verifica di «{worst_name}»"
    if never:
        note += f" — {never}/{len(facilities)} impianti mai verificati"
    return _result(float(worst_age), len(facilities), note)


# Registry kpi_code → connettore. I codici qui presenti DEVONO avere
# source="internal" nel catalogo (kpi_catalog) e nelle KPIDefinition salvate.
# ── OSINT (esposizione esterna) ──────────────────────────────────────────────
# KPI di stato, da leggere a colpo d'occhio: la tua postura esterna, i critici
# aperti sui tuoi domini e asset, e quanti fornitori critici hanno un voto
# basso. Nessun indicatore sulle segnalazioni ai fornitori: segnalare è una
# facoltà, non un obbligo.

def _osint_own_entities(plant):
    """Entità OSINT proprie del sito: i suoi domini e i suoi asset esposti."""
    from apps.assets.models import AssetIT, AssetOT, AssetSW
    from apps.osint.models import OsintEntity

    qs = OsintEntity.objects.filter(entity_type__in=["my_domain", "asset"], is_active=True)
    if plant is None:
        return qs
    asset_ids = set()
    for model in (AssetIT, AssetOT, AssetSW):
        asset_ids |= set(model.objects.filter(plant=plant).values_list("pk", flat=True))
    return qs.filter(Q(entity_type="my_domain", source_id=plant.pk) | Q(entity_type="asset", source_id__in=asset_ids))


def osint_security_score(plant, week_start) -> dict:
    """Sicurezza esterna media (0–100, più alto = meglio) di domini e asset del sito."""
    from apps.osint.scoring import security_score

    risks = [r for r in _osint_own_entities(plant).values_list("last_score_total", flat=True) if r is not None]
    if not risks:
        return _no_data("Nessun dominio o asset del sito ancora analizzato.")
    avg = sum(security_score(r) for r in risks) / len(risks)
    return _result(round(avg, 1), len(risks), f"media di {len(risks)} domini/asset")


def osint_critical_open_count(plant, week_start) -> dict:
    """Problemi OSINT critici aperti su domini e asset del sito (stato puntuale)."""
    from apps.osint.findings import OPEN_STATUSES
    from apps.osint.models import OsintFinding

    entities = _osint_own_entities(plant)
    n = entities.count()
    if n == 0:
        return _no_data("Nessun dominio o asset del sito monitorato.")
    open_crit = OsintFinding.objects.filter(
        entity__in=entities, severity="critical", status__in=OPEN_STATUSES,
    ).count()
    return _result(float(open_crit), n, f"{open_crit} critici aperti su {n} domini/asset")


def osint_critical_suppliers_at_risk_rate(plant, week_start) -> dict:
    """% dei fornitori critici (monitoraggio approfondito) con voto D o F."""
    from apps.osint.models import OsintEntity, OsintSettings
    from apps.osint.scoring import grade_for
    from apps.suppliers.models import Supplier

    qs = OsintEntity.objects.filter(entity_type="supplier", is_active=True, deep_monitoring=True,
                                    last_score_total__isnull=False)
    if plant is not None:
        # Fornitori del sito, più quelli senza siti: servono tutta l'organizzazione.
        serving = Supplier.objects.filter(Q(plants=plant) | Q(plants__isnull=True)).values("pk")
        qs = qs.filter(source_id__in=serving)
    risks = list(qs.values_list("last_score_total", flat=True))
    if not risks:
        return _no_data("Nessun fornitore critico ancora analizzato.")
    settings = OsintSettings.load()
    at_risk = sum(1 for r in risks if grade_for(r, settings) in ("D", "F"))
    return _result(_rate(at_risk, len(risks)), len(risks), f"{at_risk}/{len(risks)} fornitori critici con voto D/F")


INTERNAL_CONNECTORS = {
    "controls_compliance_rate": controls_compliance_rate,
    "evidence_expiry_rate": evidence_expiry_rate,
    "open_pdca_over_90days": open_pdca_over_90days,
    "audit_findings_open_rate": audit_findings_open_rate,
    "training_completion_rate": training_completion_rate,
    "training_plan_progress": training_plan_progress,
    "training_plan_overdue": training_plan_overdue,
    "phishing_click_rate": phishing_click_rate,
    "phishing_report_rate": phishing_report_rate,
    "board_training_valid": board_training_valid,
    "systems_eol_count": systems_eol_count,
    "incident_mttr_hours": incident_mttr_hours,
    "incident_recurrence_rate": incident_recurrence_rate,
    "incident_rca_completion_rate": incident_rca_completion_rate,
    "suppliers_assessed_rate": suppliers_assessed_rate,
    "suppliers_critical_unassessed": suppliers_critical_unassessed,
    "osint_security_score": osint_security_score,
    "osint_critical_open_count": osint_critical_open_count,
    "osint_critical_suppliers_at_risk_rate": osint_critical_suppliers_at_risk_rate,
    "dr_test_age_days": dr_test_age_days,
    "dr_test_pass_rate": dr_test_pass_rate,
    "dr_rto_gap_hours": dr_rto_gap_hours,
    "dr_plans_overdue_count": dr_plans_overdue_count,
    "bcp_critical_process_coverage": bcp_critical_process_coverage,
    "bcp_rto_meets_bia_target_rate": bcp_rto_meets_bia_target_rate,
    "maintenance_plan_compliance_rate": maintenance_plan_compliance_rate,
    "maintenance_overdue_count": maintenance_overdue_count,
    "facility_check_age_days": facility_check_age_days,
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
