from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action
from ..models import ManagementReview, ReviewAction

# Gli elenchi di dettaglio nello snapshot sono pensati per la direzione:
# pochi elementi, i più rilevanti; il totale resta nei contatori.
SNAPSHOT_LIST_LIMIT = 10

# Soglia di rischio "critico" (rosso), coerente con il resto del modulo.
CRITICAL_RISK_SCORE = 14


def _display_name(first_name, last_name, email) -> str:
    name = f"{first_name or ''} {last_name or ''}".strip()
    return name or email or ""


def _iso(value):
    return value.isoformat() if value else None


def get_operational_kpi_summary(plant_id, all_plants: bool = False) -> dict:
    """Ultimo snapshot di ogni KPI operativo rilevante per il plant.

    P2-4 (catena KPI engine → revisione direzione): la revisione di direzione
    (ISO 27001 §9.3) deve considerare i "risultati di monitoraggio e misurazione".
    Il KPI engine (M08) produce snapshot settimanali con soglie e stato, ma la
    revisione finora li ignorava. Qui aggreghiamo, per ogni `KPIDefinition`
    attiva, lo snapshot più recente rilevante per il plant — sia i KPI specifici
    del plant sia i KPI globali (snapshot per-plant prodotti dal compute, oppure
    snapshot globali `plant=None` da ingest API).
    """
    from django.db.models import Q
    from apps.tasks.models import OperationalKpiSnapshot

    snaps = (
        OperationalKpiSnapshot.objects
        .filter(Q(plant_id=plant_id) | Q(plant__isnull=True) if plant_id or not all_plants else Q())
        .filter(kpi_definition__is_active=True, kpi_definition__deleted_at__isnull=True)
        .select_related("kpi_definition", "plant")
        .order_by("kpi_definition_id", "-week_start", "-created_at")
    )

    latest: dict = {}
    for s in snaps:
        # Per ogni KPI tieni solo il primo (= più recente, per via dell'order_by);
        # a parità di plant_id/None preferisci lo snapshot legato al plant.
        # Con `all_plants` (riesame di organizzazione) un valore per ogni sito.
        key = (s.kpi_definition_id, s.plant_id) if all_plants and not plant_id else s.kpi_definition_id
        prev = latest.get(key)
        if prev is None:
            latest[key] = s
        elif prev.plant_id is None and s.plant_id is not None and s.week_start == prev.week_start:
            latest[key] = s

    status_counts = {"ok": 0, "warning": 0, "critical": 0, "no_data": 0}
    items = []
    for s in latest.values():
        kd = s.kpi_definition
        status_counts[s.status] = status_counts.get(s.status, 0) + 1
        items.append({
            "kpi_code": kd.kpi_code,
            "name": kd.name,
            "unit": kd.unit,
            "value": s.value,
            "status": s.status,
            "threshold_warning": kd.threshold_warning,
            "threshold_critical": kd.threshold_critical,
            "threshold_direction": kd.threshold_direction,
            "week_start": s.week_start.isoformat(),
            "scope": "plant" if s.plant_id else "global",
            "plant_code": s.plant.code if s.plant_id else None,
        })

    items.sort(key=lambda x: x["kpi_code"])
    return {
        "items": items,
        "count": len(items),
        "status_counts": status_counts,
        "attention": status_counts["warning"] + status_counts["critical"],
    }


def get_kpi_snapshot(plant_id) -> dict:
    """Return a dict with key metrics for the given plant."""
    from apps.controls.models import ControlInstance
    from apps.incidents.models import Incident
    from apps.risk.models import RiskAssessment

    controls_qs = ControlInstance.objects.filter(plant_id=plant_id)
    total_controls = controls_qs.count()
    compliant = controls_qs.filter(status="compliant").count()

    incidents_qs = Incident.objects.filter(plant_id=plant_id)
    open_incidents = incidents_qs.filter(status__in=["aperto", "in_analisi"]).count()

    risks_qs = RiskAssessment.objects.filter(plant_id=plant_id, status="completato")
    high_risks = risks_qs.filter(score__gt=14).count()

    return {
        "plant_id": str(plant_id),
        "controls_total": total_controls,
        "controls_compliant": compliant,
        "pct_compliant": round(compliant / total_controls * 100, 1) if total_controls else 0,
        "incidents_open": open_incidents,
        "risks_high": high_risks,
        "operational_kpis": get_operational_kpi_summary(plant_id),
        "snapshot_at": timezone.now().isoformat(),
    }


def _previous_reviews(review: ManagementReview):
    """Riesami completi precedenti dello stesso perimetro (stesso sito, o di
    organizzazione). I mirati non contano: il "periodo" del §9.3 va da un
    riesame completo all'altro."""
    return (
        ManagementReview.objects.filter(
            plant_id=review.plant_id, review_date__lt=review.review_date, kind="completo",
        )
        .exclude(pk=review.pk)
        .order_by("-review_date")
    )


def _previous_actions_block(review: ManagementReview, today) -> dict:
    """§9.3.2 a) — stato delle azioni dei riesami precedenti: tutte quelle del
    riesame immediatamente precedente, più quelle più vecchie ancora aperte o
    chiuse nel periodo. Comprese quelle decise nei riesami mirati tenuti
    dopo l'ultimo riesame completo."""
    from django.db.models import Case, IntegerField, Q, Value, When

    previous = _previous_reviews(review).first()
    empty = {"riesame_precedente": None, "totale": 0, "aperte": 0, "scadute": 0, "chiuse": 0, "elenco": []}

    base = ReviewAction.objects.filter(
        review__plant_id=review.plant_id,
        review__review_date__lt=review.review_date,
        review__deleted_at__isnull=True,
    ).exclude(review=review)
    if previous is None:
        # Primo riesame completo: restano da verificare le decisioni delle
        # sedute mirate che lo hanno preceduto.
        qs = base.filter(review__kind="mirato")
        if not qs.exists():
            return empty
    else:
        qs = base.filter(
            Q(review=previous) | Q(status="aperto") | Q(closed_at__date__gte=previous.review_date)
            | Q(review__kind="mirato", review__review_date__gte=previous.review_date)
        )
    overdue_q = Q(status="aperto", due_date__lt=today)
    rank = Case(
        When(overdue_q, then=Value(0)),
        When(status="aperto", then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    rows = (
        qs.select_related("owner", "review", "task", "pdca_cycle")
        .annotate(rank=rank)
        .order_by("rank", "due_date")[:SNAPSHOT_LIST_LIMIT]
    )
    return {
        "riesame_precedente": {
            "id": str(previous.pk), "title": previous.title, "review_date": _iso(previous.review_date),
        } if previous else None,
        "totale": qs.count(),
        "aperte": qs.filter(status="aperto").count(),
        "scadute": qs.filter(overdue_q).count(),
        "chiuse": qs.filter(status="chiuso").count(),
        "elenco": [
            {
                "id": str(a.pk),
                "description": a.description[:300],
                "owner": _display_name(a.owner.first_name, a.owner.last_name, a.owner.email) if a.owner else None,
                "due_date": _iso(a.due_date),
                "status": a.status,
                "overdue": a.status == "aperto" and bool(a.due_date) and a.due_date < today,
                "closed_at": _iso(a.closed_at),
                "review_title": a.review.title,
                "review_date": _iso(a.review.review_date),
                "task_status": a.task.status if a.task_id else None,
                "pdca_phase": a.pdca_cycle.fase_corrente if a.pdca_cycle_id else None,
            }
            for a in rows
        ],
    }


def _kpi_block(plant_id) -> dict:
    """§9.3.2 d) — risultati di monitoraggio e misurazione (KPI operativi)."""
    summary = get_operational_kpi_summary(plant_id, all_plants=not plant_id)
    rank = {"critical": 0, "warning": 1}
    attention = sorted(
        (i for i in summary["items"] if i["status"] in rank),
        key=lambda i: (rank[i["status"]], i["kpi_code"], i.get("plant_code") or ""),
    )
    keys = ("kpi_code", "name", "unit", "value", "status", "threshold_warning",
            "threshold_critical", "threshold_direction", "week_start", "plant_code")
    return {
        "totale": summary["count"],
        "status_counts": summary["status_counts"],
        "attenzione": len(attention),
        "elenco_attenzione": [{k: i.get(k) for k in keys} for i in attention[:SNAPSHOT_LIST_LIMIT]],
    }


def _objectives_block(plant_id, today) -> dict:
    """§9.3.2 d4) — stato degli obiettivi di sicurezza (§6.2).

    È il punto che finora restava scoperto: la norma chiede alla direzione di
    guardare gli obiettivi, e l'unico contenuto disponibile era la discussione
    libera. Qui si congelano stato, valore corrente e traiettoria di ogni
    obiettivo aperto del perimetro, più quelli chiusi nell'ultimo anno (il
    risultato di ciò che era stato promesso al riesame precedente).

    Un riesame di sito considera gli obiettivi del sito e quelli di
    organizzazione, che impegnano anche lui.
    """
    from django.db.models import Q
    from apps.governance.models import SecurityObjective
    from apps.governance.services import (
        OBJECTIVE_OPEN_STATUSES, evaluate_objective, latest_objective_values,
    )

    qs = SecurityObjective.objects.select_related("plant", "kpi_definition")
    if plant_id:
        qs = qs.filter(Q(plant_id=plant_id) | Q(plant__isnull=True))
    recently_closed = Q(closed_at__gte=timezone.now() - timezone.timedelta(days=365))
    objectives = list(qs.filter(Q(status__in=OBJECTIVE_OPEN_STATUSES) | recently_closed))
    values = latest_objective_values(objectives)

    counts = {"totale": len(objectives), "attivi": 0, "a_rischio": 0, "mancati": 0, "raggiunti": 0}
    items = []
    for o in objectives:
        value, measured_on = values.get(o.id, (None, None))
        ev = evaluate_objective(o, value=value, measured_on=measured_on, today=today)
        if o.status == "attivo":
            counts["attivi"] += 1
        if o.status == "raggiunto":
            counts["raggiunti"] += 1
        if o.status == "non_raggiunto" or ev["track"] == "mancato":
            counts["mancati"] += 1
        elif ev["track"] == "a_rischio":
            counts["a_rischio"] += 1
        items.append({
            "id": str(o.id),
            "code": o.code,
            "title": o.title,
            "plant_code": o.plant.code if o.plant_id else None,
            "owner_role": o.owner_role,
            "status": o.status,
            "baseline_value": o.baseline_value,
            "target_value": o.target_value,
            "target_date": _iso(o.target_date),
            "current_value": ev["current_value"],
            "unit": ev["unit"],
            "progress_pct": ev["progress_pct"],
            "track": ev["track"],
        })

    # In direzione si guardano per primi quelli che non stanno andando bene.
    order = {"mancato": 0, "a_rischio": 1, "senza_misure": 2, "in_linea": 3, "non_applicabile": 4}
    items.sort(key=lambda i: (order.get(i["track"], 9), i["target_date"] or "", i["code"]))
    return {**counts, "elenco": items[:SNAPSHOT_LIST_LIMIT]}


def _audit_block(scope: dict, today, since_12m) -> dict:
    """§9.3.2 d) — risultati degli audit e non conformità (M17)."""
    from django.db.models import Case, Count, IntegerField, Q, Value, When
    from apps.audit_prep.models import AuditFinding, AuditPrep

    prep_scope = {"plant_id": scope["plant_id"]} if scope else {}
    finding_scope = {"audit_prep__plant_id": scope["plant_id"]} if scope else {}

    audits = (
        AuditPrep.objects.filter(**prep_scope, audit_date__gte=since_12m.date())
        .select_related("framework", "plant")
        .annotate(n_findings=Count("findings", filter=Q(findings__deleted_at__isnull=True)))
        .order_by("-audit_date")
    )
    findings = AuditFinding.objects.filter(**finding_scope, audit_prep__deleted_at__isnull=True)
    open_qs = findings.filter(status__in=["open", "in_response"])
    by_type = dict(open_qs.values("finding_type").annotate(n=Count("id")).values_list("finding_type", "n"))
    nc_rank = Case(When(finding_type="major_nc", then=Value(0)), default=Value(1), output_field=IntegerField())

    def _finding(f):
        return {
            "id": str(f.pk),
            "title": f.title,
            "finding_type": f.finding_type,
            "status": f.status,
            "response_deadline": _iso(f.response_deadline),
            "overdue": bool(f.response_deadline) and f.response_deadline < today,
            "audit": f.audit_prep.title,
            "plant_code": f.audit_prep.plant.code if f.audit_prep.plant_id else None,
        }

    open_nc = (
        open_qs.filter(finding_type__in=["major_nc", "minor_nc"])
        .select_related("audit_prep__plant")
        .annotate(rank=nc_rank)
        .order_by("rank", "response_deadline")
    )
    opportunities = (
        findings.filter(finding_type="opportunity").exclude(status="closed")
        .select_related("audit_prep__plant")
        .order_by("-audit_date")
    )
    audit_rows = [
        {
            "id": str(a.pk),
            "title": a.title,
            "audit_date": _iso(a.audit_date),
            "framework": a.framework.code if a.framework_id else None,
            "status": a.status,
            "readiness_score": a.readiness_score,
            "findings": a.n_findings,
            "plant_code": a.plant.code if a.plant_id else None,
            "audit_type": a.audit_type,
            "requesting_party": a.requesting_party,
            "group": str(a.group_id) if a.group_id else None,
            "group_title": a.group.title if a.group_id else None,
        }
        for a in audits.select_related("group")
    ]
    if not scope:
        # Riesame di organizzazione: un audit multi-sito conta una volta sola,
        # con i siti coinvolti e i finding sommati (prontezza per sito omessa).
        merged, by_group = [], {}
        for row in audit_rows:
            gid = row["group"]
            if gid is None:
                merged.append(row)
            elif gid not in by_group:
                by_group[gid] = {**row, "id": gid, "title": row["group_title"],
                                 "readiness_score": None, "plant_codes": [row["plant_code"]]}
                merged.append(by_group[gid])
            else:
                g = by_group[gid]
                g["findings"] += row["findings"]
                g["plant_codes"].append(row["plant_code"])
        for g in by_group.values():
            g["plant_code"] = ", ".join(sorted(c for c in g.pop("plant_codes") if c))
        audit_rows = merged
    for row in audit_rows:
        row.pop("group_title", None)

    return {
        "audit_12m": len(audit_rows),
        "nc_aperte_maggiori": by_type.get("major_nc", 0),
        "nc_aperte_minori": by_type.get("minor_nc", 0),
        "osservazioni_aperte": by_type.get("observation", 0),
        "opportunita_aperte": opportunities.count(),
        "finding_scaduti": open_qs.filter(response_deadline__lt=today).count(),
        "finding_chiusi_12m": findings.filter(
            status__in=["closed", "accepted_by_auditor"], closed_at__gte=since_12m
        ).count(),
        "elenco_audit": audit_rows[:SNAPSHOT_LIST_LIMIT],
        "elenco_nc_aperte": [_finding(f) for f in open_nc[:SNAPSHOT_LIST_LIMIT]],
        "elenco_opportunita": [_finding(f) for f in opportunities[:SNAPSHOT_LIST_LIMIT]],
    }


def _sites_block(today) -> list[dict]:
    """Riesame di organizzazione: una riga di sintesi per sito (query aggregate)."""
    from django.db.models import Count, Q
    from apps.controls.models import ControlInstance
    from apps.incidents.models import Incident
    from apps.plants.models import Plant
    from apps.risk.models import RiskAssessment
    from apps.tasks.models import Task

    def _by_plant(qs, **annotations):
        return {row.pop("plant_id"): row for row in qs.values("plant_id").annotate(**annotations)}

    controls = _by_plant(
        ControlInstance.objects.all(),
        total=Count("id"), compliant=Count("id", filter=Q(status="compliant")),
    )
    risks = _by_plant(
        RiskAssessment.objects.filter(status="completato", score__gt=CRITICAL_RISK_SCORE), n=Count("id"),
    )
    incidents = _by_plant(Incident.objects.filter(status__in=["aperto", "in_analisi"]), n=Count("id"))
    tasks = _by_plant(
        Task.objects.filter(status__in=["aperto", "in_corso"], due_date__lt=today), n=Count("id"),
    )
    rows = []
    for plant in Plant.objects.order_by("code"):
        c = controls.get(plant.pk, {})
        total = c.get("total", 0)
        rows.append({
            "plant_id": str(plant.pk),
            "code": plant.code,
            "name": plant.name,
            "pct_compliant": round(c.get("compliant", 0) / total * 100, 1) if total else None,
            "rischi_critici": risks.get(plant.pk, {}).get("n", 0),
            "incidenti_aperti": incidents.get(plant.pk, {}).get("n", 0),
            "task_scaduti": tasks.get(plant.pk, {}).get("n", 0),
        })
    return rows


def generate_snapshot(review: ManagementReview, user) -> dict:
    """
    Congela i dati di compliance al momento della riunione.
    """
    from django.core.exceptions import ValidationError

    from .review import ensure_full_review

    ensure_full_review(review)

    if review.approval_status == "approvato":
        # Lo snapshot è il contenuto del verbale approvato: non si riscrive.
        raise ValidationError(_("Il riesame è approvato: lo snapshot non può essere rigenerato."))

    from django.db.models import Case, Count, IntegerField, Q, Value, When
    from apps.controls.models import ControlInstance
    from apps.documents.models import Document, Evidence
    from apps.risk.models import RiskAssessment
    from apps.incidents.models import Incident
    from apps.pdca.models import PdcaCycle
    from apps.tasks.models import Task

    from apps.plants.services import plant_today

    plant_id = review.plant_id
    # Riesame di organizzazione (senza sito): i dati aggregano tutti i siti.
    scope = {"plant_id": plant_id} if plant_id else {}
    today = plant_today(review.plant)
    since_12m = timezone.now() - timezone.timedelta(days=365)

    # ── 1. Compliance per framework con dettaglio ──
    from apps.plants.services import get_active_frameworks
    from apps.plants.models import Plant as PlantModel
    _plant = PlantModel.objects.filter(pk=plant_id).first() if plant_id else None

    frameworks_detail = {}
    for fw in get_active_frameworks(_plant):
        qs = ControlInstance.objects.filter(
            **scope, control__framework=fw
        ).select_related("control__domain")
        total = qs.count()
        if total == 0:
            continue
        by_status = dict(qs.values("status").annotate(n=Count("id")).values_list("status", "n"))
        compliant = by_status.get("compliant", 0)

        gap_controls = [
            {
                "id": str(item["id"]),
                "control__external_id": item["control__external_id"],
                # Solo il titolo per lingua: il JSON completo delle traduzioni
                # (guida, evidenze attese…) non serve al verbale.
                "titles": {
                    lang: (tr or {}).get("title", "")
                    for lang, tr in (item["control__translations"] or {}).items()
                    if (tr or {}).get("title")
                },
            }
            for item in qs.filter(status="gap").order_by("control__external_id").values(
                "id", "control__external_id", "control__translations",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

        expired_evidence_controls = [
            {**item, "id": str(item["id"])}
            for item in qs.filter(
                status="compliant",
                evidences__valid_until__lt=today,
            ).values("id", "control__external_id")[:10]
        ]

        frameworks_detail[fw.code] = {
            "framework_name": fw.name,
            "total": total,
            "by_status": by_status,
            "pct_compliant": round(compliant / total * 100, 1) if total else 0,
            "gap_controls": gap_controls,
            "expired_evidence_count": len(expired_evidence_controls),
        }

    # ── 2. Documenti ──
    docs_qs = Document.objects.filter(**scope, deleted_at__isnull=True)
    expiring_q = Q(
        status="approvato",
        review_due_date__lte=today + timezone.timedelta(days=90),
        review_due_date__gte=today,
    )
    expired_q = Q(status="approvato", review_due_date__lt=today)

    # "Novità" da portare in direzione: approvati dall'ultimo riesame del
    # perimetro (o negli ultimi 12 mesi se è il primo).
    previous = (
        _previous_reviews(review).first()
    )
    approved_since = previous.review_date if previous else (today - timezone.timedelta(days=365))
    approved_recent_q = Q(status="approvato", approved_at__date__gte=approved_since)

    # §9.3.2 d) — documenti obbligatori non ancora in vigore: la direzione li
    # vede per nome e decide se portarli all'approvazione. I non obbligatori
    # (contratti, NDA) restano nei conteggi, fuori dall'elenco.
    from apps.documents.services import PENDING_STATUSES

    pending_mandatory_q = Q(is_mandatory=True, status__in=PENDING_STATUSES)

    def _pending_doc_items(q):
        # La revisione che sta per essere approvata, come scritta sul
        # frontespizio del file ("Rev. 03"): è ciò che l'auditor confronta con
        # il documento in mano. Senza etichetta vale il contatore interno.
        from django.db.models import OuterRef, Subquery
        from apps.documents.models import DocumentVersion

        latest = DocumentVersion.objects.filter(document=OuterRef("pk")).order_by("-version_number")
        rows = (
            docs_qs.filter(q)
            .annotate(
                v_label=Subquery(latest.values("version_label")[:1]),
                v_number=Subquery(latest.values("version_number")[:1]),
            )
            # I più vecchi per primi: sono quelli fermi da più tempo.
            .order_by("created_at")
            .values(
                "id", "title", "document_code", "document_type", "status", "created_at",
                "v_label", "v_number",
            )[:SNAPSHOT_LIST_LIMIT]
        )
        return [
            {
                "id": str(d["id"]),
                "title": d["title"],
                "document_code": d["document_code"],
                "document_type": d["document_type"],
                "status": d["status"],
                "version": d["v_label"] or (f"v{d['v_number']}" if d["v_number"] else None),
                "created_at": _iso(d["created_at"]),
            }
            for d in rows
        ]

    def _doc_items(q, order):
        return [
            {
                "id": str(d["id"]),
                "title": d["title"],
                "owner": _display_name(d["owner__first_name"], d["owner__last_name"], d["owner__email"]),
                "review_due_date": _iso(d["review_due_date"]),
                "approved_at": _iso(d["approved_at"]),
            }
            for d in docs_qs.filter(q).order_by(order).values(
                "id", "title", "review_due_date", "approved_at",
                "owner__first_name", "owner__last_name", "owner__email",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

    docs_summary = {
        "totale": docs_qs.count(),
        "approvati": docs_qs.filter(status="approvato").count(),
        "in_revisione": docs_qs.filter(status__in=["revisione", "approvazione"]).count(),
        "bozza": docs_qs.filter(status="bozza").count(),
        "in_scadenza": docs_qs.filter(expiring_q).count(),
        "scaduti": docs_qs.filter(expired_q).count(),
        "approvati_periodo": docs_qs.filter(approved_recent_q).count(),
        "approvati_dal": approved_since.isoformat(),
        "obbligatori": docs_qs.filter(is_mandatory=True).count(),
        "non_approvati_obbligatori": docs_qs.filter(pending_mandatory_q).count(),
        "elenco_non_approvati": _pending_doc_items(pending_mandatory_q),
        "elenco_scaduti": _doc_items(expired_q, "review_due_date"),
        "elenco_in_scadenza": _doc_items(expiring_q, "review_due_date"),
        "elenco_approvati_periodo": _doc_items(approved_recent_q, "-approved_at"),
    }
    ev_scadute = Evidence.objects.filter(
        **scope, valid_until__lt=today, deleted_at__isnull=True
    ).count()
    ev_in_scadenza = Evidence.objects.filter(
        **scope,
        valid_until__gte=today,
        valid_until__lte=today + timezone.timedelta(days=30),
        deleted_at__isnull=True,
    ).count()

    # ── 3. Rischi ──
    risks_qs = RiskAssessment.objects.filter(
        **scope, status="completato", deleted_at__isnull=True
    )
    critical_qs = risks_qs.filter(score__gt=CRITICAL_RISK_SCORE)
    accepted_qs = risks_qs.filter(risk_accepted_formally=True)
    risk_summary = {
        "rosso":  critical_qs.count(),
        "giallo": risks_qs.filter(score__gt=7, score__lte=CRITICAL_RISK_SCORE).count(),
        "verde":  risks_qs.filter(score__lte=7).count(),
        "senza_piano": critical_qs.annotate(
            n_plans=Count("mitigation_plans", filter=Q(mitigation_plans__deleted_at__isnull=True))
        ).filter(n_plans=0).count(),
        "senza_owner": risks_qs.filter(owner__isnull=True).count(),
        "accettati_formalmente": accepted_qs.count(),
    }

    def _risk_items(qs, order):
        rows = (
            qs.select_related("asset", "critical_process", "owner", "risk_accepted_by")
            .annotate(n_plans=Count("mitigation_plans", filter=Q(mitigation_plans__deleted_at__isnull=True)))
            .order_by(*order)[:SNAPSHOT_LIST_LIMIT]
        )
        return [
            {
                "id": str(r.pk),
                "name": r.name or (r.asset.name if r.asset else "") or "—",
                "asset": r.asset.name if r.asset else None,
                "process": r.critical_process.name if r.critical_process else None,
                "inherent_score": r.inherent_score,
                "score": r.score,
                "treatment": r.treatment or None,
                "owner": _display_name(r.owner.first_name, r.owner.last_name, r.owner.email) if r.owner else None,
                "has_plan": r.n_plans > 0,
                "accepted_formally": r.risk_accepted_formally,
                "accepted_by": (
                    _display_name(r.risk_accepted_by.first_name, r.risk_accepted_by.last_name, r.risk_accepted_by.email)
                    if r.risk_accepted_by else None
                ),
                "acceptance_expiry": _iso(r.risk_acceptance_expiry),
            }
            for r in rows
        ]

    risk_summary["top_critici"] = _risk_items(critical_qs, ["-score", "-inherent_score"])
    risk_summary["elenco_accettati"] = _risk_items(accepted_qs, ["risk_acceptance_expiry", "-score"])

    # ── 4. Incidenti ──
    incidents_qs = Incident.objects.filter(**scope)
    open_inc_q = Q(status__in=["aperto", "in_analisi"])
    nis2_inc_q = Q(nis2_notifiable="si", created_at__gte=since_12m)

    def _incident_items(q):
        return [
            {
                "id": str(i["id"]),
                "title": i["title"],
                "detected_at": _iso(i["detected_at"]),
                "severity": i["severity"],
                "status": i["status"],
            }
            for i in incidents_qs.filter(q).order_by("-detected_at").values(
                "id", "title", "detected_at", "severity", "status",
            )[:SNAPSHOT_LIST_LIMIT]
        ]

    incidents_summary = {
        "totale_12m": incidents_qs.filter(created_at__gte=since_12m).count(),
        "nis2_notificati": incidents_qs.filter(nis2_inc_q).count(),
        "aperti": incidents_qs.filter(open_inc_q).count(),
        "senza_rca": incidents_qs.filter(status="chiuso", rca__isnull=True).count(),
        "elenco_aperti": _incident_items(open_inc_q),
        "elenco_nis2": _incident_items(nis2_inc_q),
    }

    # ── 5. PDCA ──
    blocked_q = Q(fase_corrente="plan", created_at__lt=timezone.now() - timezone.timedelta(days=90))
    pdca_qs = PdcaCycle.objects.filter(**scope)
    pdca_summary = {
        "aperti": pdca_qs.exclude(fase_corrente__in=["chiuso", "archiviato"]).count(),
        "bloccati_plan_90gg": pdca_qs.filter(blocked_q).count(),
        "chiusi_12m": pdca_qs.filter(fase_corrente="chiuso", closed_at__gte=since_12m).count(),
        "elenco_bloccati": [
            {"id": str(c["id"]), "title": c["title"], "created_at": _iso(c["created_at"])}
            for c in pdca_qs.filter(blocked_q).order_by("created_at").values(
                "id", "title", "created_at",
            )[:SNAPSHOT_LIST_LIMIT]
        ],
    }

    # ── 6. BCP ──
    from apps.bia.models import CriticalProcess
    from apps.bcp.models import BcpPlan

    critical_procs = CriticalProcess.objects.filter(
        **scope,
        criticality__gte=4,
        status="approvato",
        deleted_at__isnull=True,
    ).prefetch_related(
        Prefetch(
            "bcp_plans",
            queryset=BcpPlan.objects.filter(deleted_at__isnull=True),
        )
    )
    missing_bcp = [p for p in critical_procs if not p.bcp_plans.all()]
    bcp_summary = {
        "processi_critici_senza_bcp": len(missing_bcp),
        "nomi": [p.name for p in missing_bcp[:5]],
    }

    # ── 7. Task scaduti ──
    open_tasks_qs = Task.objects.filter(**scope, status__in=["aperto", "in_corso"])
    overdue_qs = open_tasks_qs.filter(due_date__lt=today)
    priority_rank = Case(
        When(priority="critica", then=Value(0)),
        When(priority="alta", then=Value(1)),
        When(priority="media", then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    tasks_summary = {
        "scaduti": overdue_qs.count(),
        "critici_aperti": open_tasks_qs.filter(priority="critica").count(),
        # Prima i più gravi, poi i più in ritardo.
        "elenco_scaduti": [
            {
                "id": str(t["id"]),
                "title": t["title"],
                "priority": t["priority"],
                "due_date": _iso(t["due_date"]),
                "assigned_role": t["assigned_role"],
            }
            for t in overdue_qs.annotate(rank=priority_rank).order_by("rank", "due_date").values(
                "id", "title", "priority", "due_date", "assigned_role",
            )[:SNAPSHOT_LIST_LIMIT]
        ],
    }

    snapshot = {
        "generated_at":   timezone.now().isoformat(),
        "plant_id":       str(plant_id) if plant_id else None,
        "frameworks":     frameworks_detail,
        "documenti":      {**docs_summary, "evidenze_scadute": ev_scadute, "evidenze_in_scadenza": ev_in_scadenza},
        "rischi":         risk_summary,
        "incidenti":      incidents_summary,
        "pdca":           pdca_summary,
        "bcp":            bcp_summary,
        "task":           tasks_summary,
        "azioni_precedenti": _previous_actions_block(review, today),
        "kpi":            _kpi_block(plant_id),
        "obiettivi":      _objectives_block(plant_id, today),
        "audit":          _audit_block(scope, today, since_12m),
        "siti":           [] if plant_id else _sites_block(today),
    }

    review.snapshot_data = snapshot
    review.snapshot_generated_at = timezone.now()
    review.save(update_fields=["snapshot_data", "snapshot_generated_at", "updated_at"])

    log_action(
        user=user,
        action_code="management_review.snapshot_generated",
        level="L2",
        entity=review,
        payload={"review_id": str(review.pk)},
    )
    return snapshot


