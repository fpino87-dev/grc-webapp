"""Advisor cross-cutting del Centro Operativo.

Step 1: oltre allo `schedule.drift`, gli advisor che leggono i moduli operativi
(controlli, rischio, documenti, fornitori, BIA, incidenti, accessi) sono
centralizzati qui per velocità di MVP — riusano i service/queryset esistenti, mai
nuova detection. Refactor verso `apps/<modulo>/advisors.py` quando utile.
Tutte le query sono aggregate (no N+1) e non espongono dati personali (regola #11).
"""
from __future__ import annotations

from apps.cockpit.insights import Insight, register_advisor


def _plant_names(ids) -> dict:
    from apps.plants.models import Plant
    return {str(pk): name for pk, name in Plant.objects.filter(pk__in=list(ids)).values_list("pk", "name")}


@register_advisor
def schedule_drift_advisor(context=None):
    """Drift della pianificazione: voci di `CELERY_BEAT_SCHEDULE` non allineate al
    DB (mancanti / disabilitate / orario diverso) → automazioni di compliance che
    non partono in silenzio. Riusa `evaluate_all` (stessa fonte di `verify_schedule`
    e di `/api/health/`)."""
    from apps.audit_trail.management.commands.verify_schedule import evaluate_all

    problems = [(name, status, detail) for (name, status, detail) in evaluate_all() if status != "OK"]
    if not problems:
        return []

    return [
        Insight(
            code="schedule.drift",
            module="cockpit",
            severity="warning",
            area="governance",
            action_type="navigate",
            plant_id=None,  # globale
            entity_ref={"type": "schedule", "id": "beat", "deep_link": None},
            params={
                "count": len(problems),
                "jobs": [{"name": n, "status": s, "detail": d} for n, s, d in problems[:10]],
            },
            compliance_refs=[
                {"framework": "ISO27001", "control": "A.8.16 — Monitoring activities"},
                {"framework": "NIS2", "control": "art.21 §2(b) — Continuità operativa"},
            ],
            effort_h=0.5,
            owner_role="it_infra",
        )
    ]


def _per_plant_today_q(build):
    """
    `Q` per confronti con l'"oggi" del sito (F3, timezone per Plant) senza
    rompere l'aggregazione — vedi `plants.services.per_plant_today_q`.
    """
    from apps.plants.services import per_plant_today_q

    return per_plant_today_q(build)


def _per_plant(qs_values, code, module, area, severity, owner_role, effort_h,
               compliance_refs, deep_link, extra_params=None):
    """Costruisce un Insight per ogni plant con `c > 0` da una values().annotate(c=...)."""
    rows = [(str(r["plant_id"]), r["c"]) for r in qs_values if r.get("plant_id") and r["c"] > 0]
    if not rows:
        return []
    names = _plant_names(pid for pid, _ in rows)
    out = []
    for pid, count in rows:
        params = {"count": count, "plant_name": names.get(pid, "")}
        if extra_params:
            params.update(extra_params)
        out.append(Insight(
            code=code, module=module, severity=severity, area=area,
            plant_id=str(pid),
            entity_ref={"type": "plant", "id": str(pid), "deep_link": deep_link},
            params=params, compliance_refs=compliance_refs,
            effort_h=effort_h, owner_role=owner_role,
        ))
    return out


@register_advisor
def controls_gap_advisor(context=None):
    """Controlli in gap/parziale per plant (postura di conformità incompleta).

    Riusa `controls.services.count_open_gaps_by_plant` → stessa deduplicazione
    L3→L2 e filtro framework-attivi della lista controlli, così il numero coincide
    con quello che l'utente vede nel modulo Controlli (non un conteggio grezzo)."""
    from apps.controls.services import count_open_gaps_by_plant
    rows = [{"plant_id": pid, "c": c} for pid, c in count_open_gaps_by_plant().items()]
    return _per_plant(
        rows, "controls.gap", "controls", "controls", "warning",
        owner_role="control_owner", effort_h=8.0,
        compliance_refs=[{"framework": "ISO27001", "control": "A.5.36 — Conformità"}],
        deep_link="/controls",
    )


@register_advisor
def risk_revaluation_advisor(context=None):
    """Controlli da rivalutare (`needs_revaluation`) per plant: drift di rischio.
    Riusa il service canonico (dedup L3→L2) come `controls.gap`."""
    from apps.controls.services import count_revaluation_by_plant
    rows = [{"plant_id": pid, "c": c} for pid, c in count_revaluation_by_plant().items()]
    return _per_plant(
        rows, "risk.needs_revaluation", "risk", "risk", "warning",
        owner_role="risk_manager", effort_h=2.0,
        compliance_refs=[{"framework": "NIS2", "control": "art.21 §2(a) — Gestione del rischio"}],
        deep_link="/controls",
    )


@register_advisor
def documents_expiring_advisor(context=None):
    """Documenti approvati in scadenza entro 30 giorni, per plant."""
    from django.db.models import Count
    from apps.documents.services import get_expiring_documents
    rows = get_expiring_documents(30).values("plant_id").annotate(c=Count("id"))
    return _per_plant(
        rows, "documents.expiring", "documents", "governance", "warning",
        owner_role="compliance_officer", effort_h=1.0,
        compliance_refs=[{"framework": "ISO27001", "control": "A.5.37 — Procedure documentate"}],
        deep_link="/documents",
    )


@register_advisor
def incidents_open_advisor(context=None):
    """Incidenti aperti / in analisi per plant (workflow da chiudere)."""
    from django.db.models import Count
    from apps.incidents.models import Incident
    rows = (
        Incident.objects.filter(status__in=["aperto", "in_analisi"], deleted_at__isnull=True)
        .values("plant_id").annotate(c=Count("id"))
    )
    return _per_plant(
        rows, "incidents.open", "incidents", "incidents", "info",
        owner_role="incident_manager", effort_h=2.0,
        compliance_refs=[{"framework": "NIS2", "control": "art.23 — Gestione incidenti"}],
        deep_link="/incidents",
    )


@register_advisor
def suppliers_assessment_advisor(context=None):
    """Due diligence fornitori incompleta: per i fornitori **attivi**, segnala cosa
    *manca* tra i 3 elementi che tracciamo davvero — questionario, NDA, valutazione
    interna. Una sola riga, con il dettaglio per categoria (params.categories).
    Se per un fornitore l'elemento c'è ed è valido → sotto controllo, non segnalato."""
    from apps.suppliers.services import get_supplier_assessment_gaps
    g = get_supplier_assessment_gaps()
    categories = [
        {"key": "questionnaire", "count": g["questionnaire"]},
        {"key": "nda", "count": g["nda"]},
        {"key": "evaluation", "count": g["evaluation"]},
    ]
    if g["suppliers_with_gap"] <= 0:
        return []
    return [Insight(
        code="suppliers.assessment_gaps", module="suppliers", severity="warning",
        area="supply_chain", plant_id=None,
        entity_ref={"type": "suppliers", "id": "assessment", "deep_link": "/suppliers"},
        params={
            "count": g["suppliers_with_gap"],
            "active_total": g["active_total"],
            "categories": [c for c in categories if c["count"] > 0],
        },
        compliance_refs=[{"framework": "NIS2", "control": "art.21 §2(d) — Supply chain"}],
        effort_h=2.0, owner_role="compliance_officer",
    )]


@register_advisor
def bia_resilience_advisor(context=None):
    """Gap di resilienza BIA→BCP (processi critici senza copertura BCP adeguata)."""
    from apps.bia.services import get_resilience_gap_register
    reg = get_resilience_gap_register()
    attention = reg.get("attention", 0)
    if attention <= 0:
        return []
    return [Insight(
        code="bia.resilience_gap", module="bia", severity="warning",
        area="continuity", plant_id=None,
        entity_ref={"type": "register", "id": "resilience", "deep_link": "/bia"},
        params={"count": attention, "by_level": reg.get("by_level", {})},
        compliance_refs=[{"framework": "NIS2", "control": "art.21 §2(c) — Continuità operativa"}],
        effort_h=8.0, owner_role="risk_manager",
    )]


@register_advisor
def kpi_threshold_advisor(context=None):
    """KPI operativi (M08) fuori soglia per plant. Riusa il summary canonico
    (`management_review.get_operational_kpi_summary`, include i KPI globali).
    Severità critical se almeno un KPI è critico, altrimenti warning."""
    from apps.tasks.models import OperationalKpiSnapshot
    from apps.management_review.services import get_operational_kpi_summary

    plant_ids = (
        OperationalKpiSnapshot.objects.filter(plant_id__isnull=False, deleted_at__isnull=True)
        .values_list("plant_id", flat=True).distinct()
    )
    out = []
    for pid in plant_ids:
        s = get_operational_kpi_summary(pid)
        if s["attention"] <= 0:
            continue
        sc = s["status_counts"]
        severity = "critical" if sc.get("critical", 0) > 0 else "warning"
        name = _plant_names([pid]).get(str(pid), "")
        out.append(Insight(
            code="kpi.out_of_threshold", module="tasks", severity=severity, area="governance",
            plant_id=str(pid),
            entity_ref={"type": "plant", "id": str(pid), "deep_link": "/kpi"},
            params={"count": s["attention"], "plant_name": name,
                    "warning": sc.get("warning", 0), "critical": sc.get("critical", 0)},
            compliance_refs=[{"framework": "ISO27001", "control": "§9.1 — Monitoraggio e misurazione"}],
            effort_h=2.0, owner_role="compliance_officer",
        ))
    return out


@register_advisor
def mgmt_review_overdue_advisor(context=None):
    """Riesami di direzione pianificati ma non tenuti (review_date passata
    rispetto all'"oggi" del sito)."""
    from django.db.models import Count, Q
    from apps.management_review.models import ManagementReview
    rows = (
        ManagementReview.objects.filter(status="pianificato", deleted_at__isnull=True)
        .filter(_per_plant_today_q(
            lambda today, ids: Q(plant_id__in=ids, review_date__lt=today)
        ))
        .values("plant_id").annotate(c=Count("id"))
    )
    return _per_plant(
        rows, "mgmt_review.overdue", "management_review", "governance", "info",
        owner_role="compliance_officer", effort_h=4.0,
        compliance_refs=[{"framework": "ISO27001", "control": "§9.3 — Riesame della direzione"}],
        deep_link="/management-review",
    )


@register_advisor
def ot_unmonitored_advisor(context=None):
    """Asset OT esposti su Internet ma senza FQDN/IP → l'OSINT non può monitorarli."""
    from django.db.models import Q
    from apps.assets.models import AssetOT
    count = AssetOT.objects.filter(
        internet_exposed=True, deleted_at__isnull=True,
    ).filter(
        (Q(fqdn="") | Q(fqdn__isnull=True)) & Q(ip_address__isnull=True)
    ).count()
    if count <= 0:
        return []
    return [Insight(
        code="links.ot_unmonitored", module="assets", severity="info", area="technical",
        plant_id=None,
        entity_ref={"type": "assets", "id": "ot_unmonitored", "deep_link": "/assets"},
        params={"count": count},
        compliance_refs=[{"framework": "NIS2", "control": "art.21 §2(e) — Sicurezza acquisizione/sviluppo"}],
        effort_h=0.5, owner_role="it_infra",
    )]


@register_advisor
def vacant_roles_advisor(context=None):
    """Ruoli obbligatori NIS2/ISO senza titolare attivo (buco di governance)."""
    from apps.governance.services import get_vacant_mandatory_roles
    vacant = get_vacant_mandatory_roles(None)
    if not vacant:
        return []
    return [Insight(
        code="governance.vacant_roles", module="governance", severity="critical",
        area="governance", plant_id=None,
        entity_ref={"type": "roles", "id": "vacant", "deep_link": "/governance"},
        params={"count": len(vacant), "roles": vacant},
        compliance_refs=[
            {"framework": "NIS2", "control": "art.20 — Organi di gestione"},
            {"framework": "ISO27001", "control": "A.5.2 — Ruoli e responsabilità"},
        ],
        effort_h=2.0, owner_role="super_admin",
    )]


@register_advisor
def training_overdue_advisor(context=None):
    """Formazione obbligatoria scaduta non completata (solo conteggio — regola #11)."""
    from apps.training.services import get_overdue_enrollments
    count = get_overdue_enrollments().count()
    if count <= 0:
        return []
    return [Insight(
        code="training.overdue", module="training", severity="warning",
        area="governance", plant_id=None,
        entity_ref={"type": "training", "id": "overdue", "deep_link": "/training"},
        params={"count": count},
        compliance_refs=[
            {"framework": "ISO27001", "control": "A.6.3 — Consapevolezza, istruzione e formazione"},
            {"framework": "NIS2", "control": "art.21 §2(g) — Formazione"},
        ],
        effort_h=1.0, owner_role="compliance_officer",
    )]


@register_advisor
def audit_findings_advisor(context=None):
    """Rilievi d'audit aperti / in risposta da chiudere (M17)."""
    from apps.audit_prep.models import AuditFinding
    count = AuditFinding.objects.filter(
        status__in=["open", "in_response"], deleted_at__isnull=True,
    ).count()
    if count <= 0:
        return []
    return [Insight(
        code="audit_prep.open_findings", module="audit_prep", severity="warning",
        area="governance", plant_id=None,
        entity_ref={"type": "audit_prep", "id": "findings", "deep_link": "/audit-prep"},
        params={"count": count},
        compliance_refs=[{"framework": "ISO27001", "control": "§9.2 — Audit interni / §10.1 — Non conformità"}],
        effort_h=4.0, owner_role="compliance_officer",
    )]


@register_advisor
def audit_program_overdue_advisor(context=None):
    """Audit del **programma annuale** in ritardo (M17, ISO 27001 §9.2).

    Riusa il service canonico `count_overdue_program_audits_by_plant`: audit
    pianificati nei programmi attivi (`approvato`/`in_corso`) con `planned_date`
    già passata e non ancora chiusi. È l'esecuzione del programma di audit
    interno (clausola 9.2), distinta dai rilievi (`audit_prep.open_findings`)."""
    from apps.audit_prep.services import count_overdue_program_audits_by_plant
    rows = count_overdue_program_audits_by_plant()
    return _per_plant(
        rows, "audit_prep.program_audit_overdue", "audit_prep", "governance", "warning",
        owner_role="compliance_officer", effort_h=6.0,
        compliance_refs=[{"framework": "ISO27001", "control": "§9.2 — Programma di audit interno"}],
        deep_link="/audit-prep",
    )


@register_advisor
def documents_required_missing_advisor(context=None):
    """Documenti obbligatori **mancanti** (non solo in scadenza) per plant.

    Per ogni framework attivo del plant riusa il service canonico
    `compliance_schedule.get_required_documents_status` (stesso semaforo della
    pagina Documenti richiesti) e conta i documenti obbligatori in stato `red`
    (assenti). Un documento richiesto e non presente è un gap di conformità
    diverso dalla scadenza (`documents.expiring`): qui manca del tutto."""
    from apps.plants.models import Plant
    from apps.plants.services import get_active_framework_codes
    from apps.compliance_schedule.services import get_required_documents_status

    rows = []
    for plant in Plant.objects.filter(deleted_at__isnull=True):
        missing = 0
        for fw in get_active_framework_codes(plant):
            for item in get_required_documents_status(plant=plant, framework=fw):
                if item.get("mandatory") and item.get("traffic_light") == "red":
                    missing += 1
        if missing > 0:
            rows.append({"plant_id": str(plant.pk), "c": missing})
    return _per_plant(
        rows, "documents.required_missing", "documents", "governance", "warning",
        owner_role="compliance_officer", effort_h=4.0,
        compliance_refs=[
            {"framework": "ISO27001", "control": "§7.5 — Informazioni documentate"},
            {"framework": "NIS2", "control": "art.21 §2(a) — Politiche di sicurezza"},
        ],
        deep_link="/documents",
    )


@register_advisor
def bcp_expired_untested_advisor(context=None):
    """Piani BCP approvati **scaduti di test o mai testati** per plant.

    Un BCP che non viene esercitato non dà garanzie di continuità: si segnala
    chi ha `next_test_date` passata (test in ritardo, "oggi" del sito) o
    `last_test_date` assente (mai testato). Query aggregata, no N+1."""
    from django.db.models import Count, Q
    from apps.bcp.models import BcpPlan
    rows = (
        BcpPlan.objects.filter(status="approvato", deleted_at__isnull=True)
        .filter(_per_plant_today_q(
            lambda today, ids: Q(plant_id__in=ids)
            & (Q(last_test_date__isnull=True) | Q(next_test_date__lt=today))
        ))
        .values("plant_id").annotate(c=Count("id"))
    )
    return _per_plant(
        rows, "bcp.expired_untested", "bcp", "continuity", "warning",
        owner_role="risk_manager", effort_h=8.0,
        compliance_refs=[
            {"framework": "NIS2", "control": "art.21 §2(c) — Continuità operativa"},
            {"framework": "ISO27001", "control": "A.5.30 — Continuità ICT"},
        ],
        deep_link="/bcp",
    )


@register_advisor
def risk_open_high_advisor(context=None):
    """Rischi residui **alti (rosso) non accettati formalmente**, per plant.

    `risk_level` è una *property* (dipende da `weighted_score`/criticità BIA),
    quindi si valuta in Python su un queryset ristretto (non archiviati, non
    accettati formalmente) con `select_related` del processo critico (no N+1).
    Un rischio rosso accettato formalmente è una decisione consapevole → escluso."""
    from collections import Counter
    from apps.risk.models import RiskAssessment
    qs = (
        RiskAssessment.objects.filter(deleted_at__isnull=True, risk_accepted_formally=False)
        .exclude(status="archiviato")
        .select_related("critical_process")
    )
    tally = Counter(
        str(a.plant_id) for a in qs if a.plant_id and a.risk_level == "rosso"
    )
    rows = [{"plant_id": pid, "c": c} for pid, c in tally.items()]
    return _per_plant(
        rows, "risk.open_high", "risk", "risk", "warning",
        owner_role="risk_manager", effort_h=8.0,
        compliance_refs=[
            {"framework": "NIS2", "control": "art.21 §2(a) — Gestione del rischio"},
            {"framework": "ISO27001", "control": "§6.1 — Trattamento del rischio"},
        ],
        deep_link="/risk",
    )


@register_advisor
def risk_acceptance_expiring_advisor(context=None):
    """Accettazioni di rischio **in scadenza** (entro 30g) o già scadute, per plant.

    Quando la `risk_acceptance_expiry` decade, il rischio torna *non gestito*:
    va rinnovato o trattato. Query aggregata, no N+1; la finestra di 30 giorni
    parte dall'"oggi" del sito."""
    from datetime import timedelta
    from django.db.models import Count, Q
    from apps.risk.models import RiskAssessment
    rows = (
        RiskAssessment.objects.filter(
            deleted_at__isnull=True, risk_accepted_formally=True,
            risk_acceptance_expiry__isnull=False,
        ).exclude(status="archiviato")
        .filter(_per_plant_today_q(
            lambda today, ids: Q(
                plant_id__in=ids,
                risk_acceptance_expiry__lte=today + timedelta(days=30),
            )
        ))
        .values("plant_id").annotate(c=Count("id"))
    )
    return _per_plant(
        rows, "risk.acceptance_expiring", "risk", "risk", "warning",
        owner_role="risk_manager", effort_h=2.0,
        compliance_refs=[
            {"framework": "ISO27001", "control": "§8.3 — Trattamento del rischio"},
            {"framework": "NIS2", "control": "art.21 §2(a) — Gestione del rischio"},
        ],
        deep_link="/risk",
    )


@register_advisor
def incidents_nis2_deadline_advisor(context=None):
    """Scadenze di notifica NIS2 **imminenti o già violate** su incidenti
    significativi aperti, per plant — **critico**.

    Riproduce la stessa logica del task `check_nis2_deadlines` (M09) ma per la
    vista del Centro: incidenti `nis2_notifiable="si"` ancora aperti/in analisi,
    con `early_warning_deadline` (solo entità essenziali) o
    `formal_notification_deadline` entro 24h **o già passata** e **non ancora
    notificata**. Una notifica NIS2 mancata è una violazione di legge (art.23)."""
    from datetime import timedelta
    from collections import Counter
    from django.utils import timezone
    from apps.incidents.models import Incident
    now = timezone.now()
    horizon = now + timedelta(hours=24)
    qs = (
        Incident.objects.filter(
            nis2_notifiable="si", status__in=["aperto", "in_analisi"],
            deleted_at__isnull=True,
        ).select_related("plant").prefetch_related("nis2_notifications")
    )
    tally = Counter()
    for inc in qs:
        if not inc.plant_id:
            continue
        notif_types = {n.notification_type for n in inc.nis2_notifications.all()}
        breached = False
        entity = inc.plant.nis2_scope if inc.plant else "importante"
        if (entity == "essenziale" and inc.early_warning_deadline
                and inc.early_warning_deadline <= horizon
                and "early_warning" not in notif_types):
            breached = True
        if (inc.formal_notification_deadline and inc.formal_notification_deadline <= horizon
                and "formal_notification" not in notif_types):
            breached = True
        if breached:
            tally[str(inc.plant_id)] += 1
    rows = [{"plant_id": pid, "c": c} for pid, c in tally.items()]
    return _per_plant(
        rows, "incidents.nis2_deadline", "incidents", "incidents", "critical",
        owner_role="incident_manager", effort_h=1.0,
        compliance_refs=[{"framework": "NIS2", "control": "art.23 — Obblighi di notifica (24h/72h)"}],
        deep_link="/incidents",
    )


@register_advisor
def role_expiring_advisor(context=None):
    """Assegnazioni di ruolo in scadenza entro 30 giorni (solo conteggio — regola #11)."""
    from datetime import timedelta
    from django.utils import timezone
    from apps.governance.models import RoleAssignment
    cutoff = timezone.localdate() + timedelta(days=30)
    count = RoleAssignment.objects.filter(
        valid_until__isnull=False, valid_until__lte=cutoff,
        valid_until__gte=timezone.localdate(), deleted_at__isnull=True,
    ).count()
    if count <= 0:
        return []
    return [Insight(
        code="access.role_expiring", module="governance", severity="warning",
        area="governance", plant_id=None,
        entity_ref={"type": "roles", "id": "expiring", "deep_link": "/settings/roles"},
        params={"count": count},
        compliance_refs=[{"framework": "ISO27001", "control": "A.5.18 — Diritti di accesso"}],
        effort_h=1.0, owner_role="compliance_officer",
    )]
