from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import RiskAssessment


def mark_needs_revaluation_if_risk_changed(assessment: RiskAssessment, changed_fields: set[str]) -> None:
    """
    Se l'utente modifica campi che impattano score/ALE, segnala che serve rivalutazione.
    """
    if assessment.status == "archiviato":
        return

    risk_fields = {
        "assessment_type",
        "critical_process",
        "treatment",
        "probability",
        "impact",
        "inherent_probability",
        "inherent_impact",
    }
    if not (risk_fields & changed_fields):
        return

    assessment.needs_revaluation = True
    assessment.needs_revaluation_since = timezone.localdate()
    assessment.save(update_fields=["needs_revaluation", "needs_revaluation_since", "updated_at"])


def normalize_mixed_owner(attrs: dict, user_field: str, text_field: str) -> dict:
    """
    Responsabile "misto" (utente del portale OPPURE testo libero): i due valori
    sono alternativi. Se nel payload c'è un utente il testo viene svuotato; il
    testo viene ripulito dagli spazi. Si toccano solo i campi presenti nel
    payload, così un PATCH parziale non cancella l'altro valore.
    """
    if text_field in attrs:
        attrs[text_field] = (attrs[text_field] or "").strip()
    if attrs.get(user_field) is not None:
        attrs[text_field] = ""
    elif attrs.get(text_field):
        # Testo inviato (anche da solo, su un record che aveva un utente): vince il testo.
        attrs[user_field] = None
    return attrs


def mixed_owner_name(user, external: str) -> str | None:
    """Nome visualizzato del responsabile misto (utente o testo libero)."""
    if user is not None:
        return f"{user.first_name} {user.last_name}".strip() or user.email
    return external or None


IT_WEIGHTS = {
    "esposizione": 0.30,
    "cve": 0.25,
    "minaccia": 0.25,
    "gap_controlli": 0.20,
}
OT_WEIGHTS = {
    "purdue_connettivita": 0.25,
    "patchability": 0.20,
    "impatto_fisico": 0.25,
    "segmentazione": 0.15,
    "rilevabilita": 0.15,
}


def calc_score(assessment: RiskAssessment) -> int:
    dims = {d.dimension_code: d.value for d in assessment.dimensions.all()}
    weights = IT_WEIGHTS if assessment.assessment_type == "IT" else OT_WEIGHTS
    weighted = sum(dims.get(k, 3) * w for k, w in weights.items())
    prob = min(5, round(weighted))
    impact = min(5, round(weighted))
    return min(25, prob * impact)


def calc_ale(assessment: RiskAssessment, inherent: bool = False) -> Decimal:
    """
    Calcola ALE annuo partendo dai dati BIA del processo critico collegato.
    Formula: downtime_cost_hour × ore_fermo_stimato × probabilità_annua
    Se non c'è processo BIA collegato restituisce Decimal("0").

    inherent=False (default) → ALE residua: usa probabilità/impatto post-controlli
    (i campi correnti dell'assessment). inherent=True → ALE inerente: usa i campi
    inherent_* (rischio prima dei controlli); se non valorizzati ricade sui residui,
    così l'ALE inerente non risulta mai inferiore alla residua per dati mancanti.
    La differenza inerente − residua quantifica in € il rischio abbattuto dai controlli.
    """
    if not assessment.critical_process:
        return Decimal("0")
    cp = assessment.critical_process
    if not cp.downtime_cost_hour:
        return Decimal("0")
    ore_fermo_map = {1: 1, 2: 4, 3: 24, 4: 72, 5: 168}
    prob_annua_map = {1: 0.1, 2: 0.3, 3: 1.0, 4: 3.0, 5: 10.0}
    if inherent:
        impact = assessment.inherent_impact or assessment.impact or 3
        prob = assessment.inherent_probability or assessment.probability or 3
    else:
        impact = assessment.impact or 3
        prob = assessment.probability or 3
    ore = ore_fermo_map.get(impact, 24)
    prob_a = prob_annua_map.get(prob, 1.0)
    ale = Decimal(str(cp.downtime_cost_hour)) * Decimal(str(ore)) * Decimal(str(prob_a))
    extra = Decimal("1.0")
    if cp.danno_reputazionale >= 4:
        extra += Decimal("0.3")
    if cp.danno_normativo >= 4:
        extra += Decimal("0.2")
    return (ale * extra).quantize(Decimal("0.01"))


def calc_score_from_dimensions(assessment: RiskAssessment) -> int:
    """Score pesato con RiskDimension IT/OT — usato quando disponibili."""
    dims = {d.dimension_code: d.value for d in assessment.dimensions.all()}
    if not dims:
        p = assessment.probability or 1
        i = assessment.impact or 1
        return min(25, p * i)
    weights = IT_WEIGHTS if assessment.assessment_type == "IT" else OT_WEIGHTS
    weighted = sum(dims.get(k, 3) * w for k, w in weights.items())
    prob = min(5, round(weighted))
    impact = min(5, round(weighted))
    return min(25, prob * impact)


def suggest_residual_score(assessment) -> dict:
    """
    Suggerisce il rischio residuo in base ai controlli compliant collegati al sito.
    Logica:
    - parte dal rischio inerente
    - applica riduzione per controlli compliant (-2%, max 60%)
    - applica una riduzione extra per un BCP valido "best-match" al processo BIA
      (+10 / +5 / +0), scegliendo il piano migliore tra quelli approvati e non scaduti.
    """
    if not assessment.inherent_score:
        return {"suggested": None, "reason": "Rischio inerente non definito"}

    if not assessment.critical_process:
        return {
            "suggested": assessment.inherent_score,
            "reason": "Nessun processo BIA collegato — nessuna riduzione applicata",
        }

    from apps.controls.models import ControlInstance
    plant_controls = ControlInstance.objects.filter(
        plant=assessment.plant,
        status="compliant",
        deleted_at__isnull=True,
    )
    compliant_count = plant_controls.count()
    reduction_pct = min(60, compliant_count * 2)

    # ─── BCP contribution (best valid plan for this process) ─────────────────
    bcp_extra_pct = 0
    best_bcp_title = None
    best_bcp_strength = 0.0

    try:
        import datetime
        from django.db.models import Q
        from django.utils import timezone

        from apps.bcp.models import BcpPlan

        process = assessment.critical_process
        today = timezone.localdate()
        rto_target = process.rto_target_hours
        rpo_target = process.rpo_target_hours

        # Considero solo piani BCP approvati e non scaduti, collegati al processo BIA.
        # Nota: nel tuo modello esistono sia FK (critical_process) sia M2M (critical_processes).
        valid_plans_qs = (
            BcpPlan.objects.filter(
                deleted_at__isnull=True,
                status="approvato",
                next_test_date__isnull=False,
                next_test_date__gte=today,
            )
            .filter(Q(critical_process=process) | Q(critical_processes=process))
            .distinct()
        )

        best_key = None

        for plan in valid_plans_qs:
            last_test = (
                plan.tests.filter(deleted_at__isnull=True).order_by("-test_date").first()
            )

            rto_ok = None
            rpo_ok = None

            if rto_target is not None:
                if last_test and last_test.rto_achieved_hours is not None:
                    rto_ok = last_test.rto_achieved_hours <= rto_target
                elif plan.rto_hours is not None:
                    rto_ok = plan.rto_hours <= rto_target

            if rpo_target is not None:
                if last_test and last_test.rpo_achieved_hours is not None:
                    rpo_ok = last_test.rpo_achieved_hours <= rpo_target
                elif plan.rpo_hours is not None:
                    rpo_ok = plan.rpo_hours <= rpo_target

            known = sum(v is not None for v in (rto_ok, rpo_ok))
            strength = ((1 if rto_ok else 0) + (1 if rpo_ok else 0)) / known if known else 0.0

            achieved_data_count = 0
            if last_test:
                achieved_data_count = int(
                    (last_test.rto_achieved_hours is not None)
                    + (last_test.rpo_achieved_hours is not None)
                )

            # Tie-breakers: strength -> test più recente -> presenza dati achieved
            last_test_date = last_test.test_date if last_test else datetime.date.min
            key = (strength, last_test_date, achieved_data_count)

            if best_key is None or key > best_key:
                best_key = key
                best_bcp_strength = strength
                best_bcp_title = plan.title

        if best_bcp_title:
            if best_bcp_strength >= 1.0:
                bcp_extra_pct = 10
            elif best_bcp_strength >= 0.5:
                bcp_extra_pct = 5
            else:
                bcp_extra_pct = 0

    except Exception:
        # Non deve bloccare la UI: se BCP non è disponibile o qualche campo è mancante,
        # continuiamo con la sola riduzione da controlli.
        bcp_extra_pct = 0

    total_reduction_pct = min(70, reduction_pct + bcp_extra_pct)
    suggested = max(1, round(assessment.inherent_score * (1 - total_reduction_pct / 100)))

    return {
        "suggested": suggested,
        "reduction_pct": reduction_pct,
        "compliant_controls": compliant_count,
        "bcp_extra_pct": bcp_extra_pct,
        "best_bcp_strength": best_bcp_strength,
        "reason": (
            f"{compliant_count} controlli compliant → "
            f"riduzione controlli {reduction_pct}% "
            f"(extra BCP {bcp_extra_pct}%) → "
            f"score residuo suggerito: {suggested}"
        ),
    }


def accept_risk(assessment, user, note: str, expiry_date=None) -> None:
    """Accettazione formale del rischio residuo. Richiede nota obbligatoria."""
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _
    from core.audit import log_action

    risk_lv = assessment.risk_level
    # La validazione precede ogni scrittura: resta fuori dalla transazione.
    if risk_lv != "rosso" and not note:
        raise ValidationError(_("La nota è obbligatoria per l'accettazione formale del rischio."))
    if risk_lv == "rosso" and len(note.strip()) < 50:
        raise ValidationError(
            _("Per rischi critici (rosso) la nota di accettazione deve essere di almeno 50 caratteri.")
        )

    # Accettazione formale (L1) + audit: insieme, per non lasciare un'accettazione
    # senza la sua traccia append-only (o viceversa).
    with transaction.atomic():
        assessment.risk_accepted_formally = True
        assessment.risk_accepted = True  # allineato al flag semplice usato da PDCA/notifiche
        assessment.risk_accepted_by = user
        assessment.risk_accepted_at = timezone.now()
        assessment.risk_acceptance_note = note
        assessment.risk_acceptance_expiry = expiry_date
        assessment.save(update_fields=[
            "risk_accepted_formally", "risk_accepted",
            "risk_accepted_by", "risk_accepted_at",
            "risk_acceptance_note", "risk_acceptance_expiry", "updated_at",
        ])

        log_action(
            user=user,
            action_code="risk.accepted_formally",
            level="L1",
            entity=assessment,
            payload={
                "score": assessment.score,
                "level": risk_lv,
                "note": note[:100],
                "expiry": str(expiry_date) if expiry_date else None,
            },
        )


def get_active_appetite(plant=None, framework_code: str = ""):
    """
    Recupera la policy di risk appetite attiva.
    Priorita': plant-specific > org-wide.
    """
    from django.db.models import Q
    from .models import RiskAppetitePolicy

    today = timezone.localdate()
    base_qs = RiskAppetitePolicy.objects.filter(
        valid_from__lte=today,
        deleted_at__isnull=True,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )

    if plant and framework_code:
        policy = base_qs.filter(plant=plant, framework_code=framework_code).first()
        if policy:
            return policy

    if plant:
        policy = base_qs.filter(plant=plant, framework_code="").first()
        if policy:
            return policy

    return base_qs.filter(plant__isnull=True).first()


# Soglia di accettabilità se non c'è una RiskAppetitePolicy attiva.
DEFAULT_ACCEPTABLE_SCORE = 14


class AppetiteThresholds:
    """Soglia di accettabilità per sito, con cache: policy del sito, altrimenti
    di organizzazione, altrimenti DEFAULT_ACCEPTABLE_SCORE. Regola unica per
    escalation, Reporting e riesame di direzione (M13)."""

    def __init__(self):
        self._cache: dict = {}

    def for_plant(self, plant_id) -> int:
        from apps.plants.models import Plant

        if plant_id not in self._cache:
            plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
            policy = get_active_appetite(plant=plant)
            self._cache[plant_id] = policy.max_acceptable_score if policy else DEFAULT_ACCEPTABLE_SCORE
        return self._cache[plant_id]

    def is_over(self, plant_id, score) -> bool:
        return score is not None and score > self.for_plant(plant_id)

    def over_ids(self, risk_qs) -> list:
        """ID dei rischi del queryset oltre la soglia del proprio sito."""
        return [
            pk for pk, plant_id, score in risk_qs.values_list("pk", "plant_id", "score")
            if self.is_over(plant_id, score)
        ]

    def thresholds_seen(self) -> set:
        return set(self._cache.values())


def appetite_summary(plant_id, thresholds: "AppetiteThresholds | None" = None) -> dict:
    """Soglia da mostrare per il perimetro (sito, o organizzazione se None)."""
    from apps.plants.models import Plant

    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
    policy = get_active_appetite(plant=plant)
    return {
        "defined": policy is not None,
        "max_acceptable_score": policy.max_acceptable_score if policy else DEFAULT_ACCEPTABLE_SCORE,
        "max_red_risks_count": policy.max_red_risks_count if policy else None,
        "max_unacceptable_score": policy.max_unacceptable_score if policy else None,
        # Senza sito le soglie possono variare fra siti: quella mostrata è di
        # organizzazione, i conteggi usano quella di ciascun sito.
        "per_plant": not plant_id and thresholds is not None and len(thresholds.thresholds_seen()) > 1,
    }


def escalate_red_risk(assessment: RiskAssessment, user):
    from apps.tasks.services import create_task

    appetite = get_active_appetite(plant=assessment.plant)
    threshold = appetite.max_acceptable_score if appetite else DEFAULT_ACCEPTABLE_SCORE

    if not assessment.score or assessment.score <= threshold:
        return

    # Creazione task di escalation atomica: i due task (mitigazione + soglia CISO)
    # si committano insieme. Se chiamata dentro un'altra transazione (es. risk.complete)
    # diventa un savepoint, restando coerente con la scrittura dell'assessment.
    with transaction.atomic():
        create_task(
            plant=assessment.plant,
            title=f"Piano mitigazione rischio critico — {assessment.asset}",
            priority="critica",
            source_module="M06",
            source_id=assessment.pk,
            due_date=timezone.localdate() + timezone.timedelta(days=15),
            assign_type="role",
            assign_value="risk_manager",
        )

        # Notifica CISO se troppi rischi rossi
        if appetite:
            red_count = assessment.__class__.objects.filter(
                plant=assessment.plant,
                score__gt=threshold,
                deleted_at__isnull=True,
            ).count()
            if red_count > appetite.max_red_risks_count:
                create_task(
                    plant=assessment.plant,
                    title=f"Soglia rischi critici superata ({red_count} rischi)",
                    priority="critica",
                    source_module="M06",
                    source_id=assessment.pk,
                    due_date=timezone.localdate() + timezone.timedelta(days=7),
                    assign_type="role",
                    assign_value="ciso",
                )

    # Notifica via email best-effort: schedulata su on_commit così parte solo dopo
    # il commit della transazione (niente email per un'escalation poi annullata),
    # e mai blocca la logica principale.
    def _notify_risk_red():
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification(
                "risk_red",
                plant=assessment.plant,
                context={"assessment": assessment},
            )
        except Exception:
            pass

    transaction.on_commit(_notify_risk_red)


def get_risk_bia_bcp_context(assessment: RiskAssessment) -> dict:
    """
    Vista integrata per una singola valutazione di rischio:
    Rischio + BIA del processo collegato + BCP che coprono quel processo.
    Nessun side-effect, solo read-model.
    """
    from apps.bia.models import CriticalProcess
    from apps.bcp.models import BcpPlan

    risk_data = {
        "id": str(assessment.pk),
        "name": assessment.name,
        "assessment_type": assessment.assessment_type,
        "asset_id": str(assessment.asset_id) if assessment.asset_id else None,
        "probability": assessment.probability,
        "impact": assessment.impact,
        "score": assessment.score,
        "inherent_probability": assessment.inherent_probability,
        "inherent_impact": assessment.inherent_impact,
        "inherent_score": assessment.inherent_score,
        "residual_score": assessment.residual_score,
        "risk_level": assessment.risk_level,
        "inherent_risk_level": assessment.inherent_risk_level,
        "risk_reduction_pct": assessment.risk_reduction_pct,
        "status": assessment.status,
        "treatment": assessment.treatment,
        "risk_accepted_formally": assessment.risk_accepted_formally,
        "risk_acceptance_expiry": assessment.risk_acceptance_expiry,
        "needs_revaluation": assessment.needs_revaluation,
        "needs_revaluation_since": assessment.needs_revaluation_since,
    }

    bia_data = None
    bcp_plans = []
    bcp_summary = None

    process: CriticalProcess | None = assessment.critical_process
    if process:
        bia_data = {
            "process_id": str(process.pk),
            "process_name": process.name,
            "plant_id": str(process.plant_id),
            "criticality": process.criticality,
            "mtpd_hours": process.mtpd_hours,
            "rto_target_hours": process.rto_target_hours,
            "rpo_target_hours": process.rpo_target_hours,
            "downtime_cost_hour": process.downtime_cost_hour,
            "danno_reputazionale": process.danno_reputazionale,
            "danno_normativo": process.danno_normativo,
            "danno_operativo": process.danno_operativo,
            "status": process.status,
        }

        direct_plans = BcpPlan.objects.filter(
            deleted_at__isnull=True,
            critical_process=process,
        )
        m2m_plans = BcpPlan.objects.filter(
            deleted_at__isnull=True,
            critical_processes=process,
        ).exclude(pk__in=direct_plans.values_list("pk", flat=True))

        # union() non supporta select_related — si usa values() per evitare query N+1
        combined_ids = list(direct_plans.values_list("pk", flat=True)) + list(m2m_plans.values_list("pk", flat=True))
        plans_qs = BcpPlan.objects.filter(pk__in=combined_ids).select_related("plant")

        for p in plans_qs:
            bcp_plans.append(
                {
                    "id": str(p.pk),
                    "title": p.title,
                    "plant_id": str(p.plant_id),
                    "status": p.status,
                    "rto_hours": p.rto_hours,
                    "rpo_hours": p.rpo_hours,
                    "last_test_date": p.last_test_date,
                    "next_test_date": p.next_test_date,
                }
            )

        bcp_summary = {
            "has_bcp_covering_process": len(bcp_plans) > 0,
            "best_rto_vs_mtpd_status": process.rto_bcp_status,
        }

    return {
        "risk": risk_data,
        "bia": bia_data,
        "bcp_plans": bcp_plans,
        "bcp_summary": bcp_summary,
    }


@transaction.atomic
def delete_risk_assessment(assessment: RiskAssessment, user) -> None:
    """
    Soft delete del RiskAssessment e delle sue entità dipendenti (dimensions, mitigation_plans).

    Atomica: il soft-delete a cascata (dimensions + mitigation_plans + assessment) e i
    relativi audit log devono committarsi insieme, altrimenti restano entità orfane
    parzialmente cancellate o audit trail incoerente.
    """
    from core.audit import log_action

    # Dimensions + mitigation plans sono collegate via FK e soft delete rispettando l'audit trail.
    for dim in assessment.dimensions.all():
        dim.soft_delete()
        log_action(
            user=user,
            action_code="risk.dimension.deleted",
            level="L2",
            entity=dim,
            payload={"id": str(dim.id), "dimension_code": dim.dimension_code},
        )

    for mp in assessment.mitigation_plans.all():
        mp.soft_delete()
        log_action(
            user=user,
            action_code="risk.mitigation_plan.deleted",
            level="L2",
            entity=mp,
            payload={"id": str(mp.id), "due_date": str(mp.due_date)},
        )

    assessment.soft_delete()
    log_action(
        user=user,
        action_code="risk.assessment.deleted",
        level="L2",
        entity=assessment,
        payload={"id": str(assessment.id), "name": assessment.name},
    )


def generate_risk_excel(plant_id=None, include_draft: bool = False) -> bytes:
    """
    Genera il Risk Register in formato Excel (.xlsx) e restituisce i bytes.
    Riutilizzato sia dall'endpoint di export che dall'AuditPackageView.
    """
    import io
    from django.db.models import Prefetch
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from .models import NIS2_ART21_CHOICES, NIS2_RELEVANCE_CHOICES, RiskMitigationPlan

    plans_prefetch = Prefetch(
        "mitigation_plans",
        queryset=RiskMitigationPlan.objects.select_related("owner").order_by("due_date"),
    )
    qs = (
        RiskAssessment.objects
        .select_related("plant", "owner", "treatment_owner", "risk_accepted_by", "critical_process")
        .prefetch_related(plans_prefetch)
        .filter(deleted_at__isnull=True)
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    if not include_draft:
        qs = qs.filter(status="completato")

    art21_map = dict(NIS2_ART21_CHOICES)
    relevance_map = dict(NIS2_RELEVANCE_CHOICES)
    prob_labels = {1: "Molto bassa", 2: "Bassa", 3: "Media", 4: "Alta", 5: "Molto alta"}
    impact_labels = {1: "Trascurabile", 2: "Minore", 3: "Moderato", 4: "Grave", 5: "Critico"}
    level_labels = {"verde": "Basso", "giallo": "Medio", "rosso": "Alto/Critico"}
    treatment_labels = {
        "mitigare": "Mitigare", "accettare": "Accettare",
        "trasferire": "Trasferire", "evitare": "Evitare",
    }

    headers = [
        "Nome / Scenario", "Causa", "Conseguenza",
        "Tipo (IT/OT)", "Categoria minaccia", "Owner", "Responsabile trattamento",
        "Prob. inerente", "Impatto inerente", "Score inerente",
        "Probabilità residua", "Impatto residuo", "Score residuo", "Livello rischio",
        "ALE (€)",
        "Trattamento", "Scadenza piano",
        "Azioni di mitigazione",
        "Rischio accettato (Art.20)", "Accettato da", "Data accettazione",
        "Scadenza accettazione", "Nota accettazione",
        "Sistemi impattati (NIS2)", "Art.21 NIS2", "Rilevanza NIS2",
        "Processo BIA", "Plant", "Stato",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Risk Register"

    header_fill = PatternFill("solid", fgColor="1E3A5F")
    accept_fill = PatternFill("solid", fgColor="1A5276")
    nis2_fill   = PatternFill("solid", fgColor="0F5E3A")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    nis2_cols   = {headers.index(h) for h in ("Sistemi impattati (NIS2)", "Art.21 NIS2", "Rilevanza NIS2")}
    accept_cols = {headers.index(h) for h in (
        "Rischio accettato (Art.20)", "Accettato da", "Data accettazione",
        "Scadenza accettazione", "Nota accettazione",
    )}

    for col_idx, header in enumerate(headers, 1):
        i = col_idx - 1
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = nis2_fill if i in nis2_cols else (accept_fill if i in accept_cols else header_fill)
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    level_colors = {"verde": "C6EFCE", "giallo": "FFEB9C", "rosso": "FFC7CE"}

    for row_idx, risk in enumerate(qs.order_by("created_at"), 2):
        def _name(u):
            if not u:
                return ""
            return f"{u.first_name} {u.last_name}".strip() or u.email

        plans_text = "\n".join(
            f"• {p.action}"
            + (f" [{mixed_owner_name(p.owner, p.owner_external)}]" if (p.owner or p.owner_external) else "")
            + f" — Scad: {p.due_date} — {'✓ Completato' if p.completed_at else 'In corso'}"
            for p in risk.mitigation_plans.all()
        )

        ale_val = calc_ale(risk)
        ale_str = str(ale_val) if ale_val else (str(risk.ale_annuo) if risk.ale_annuo else "")

        row = [
            risk.name, risk.cause, risk.consequence,
            risk.assessment_type,
            risk.get_threat_category_display() if risk.threat_category else "",
            _name(risk.owner),
            mixed_owner_name(risk.treatment_owner, risk.treatment_owner_external) or "",
            prob_labels.get(risk.inherent_probability, ""),
            impact_labels.get(risk.inherent_impact, ""),
            risk.inherent_score or "",
            prob_labels.get(risk.probability, ""),
            impact_labels.get(risk.impact, ""),
            risk.score or "",
            level_labels.get(risk.risk_level, ""),
            ale_str,
            treatment_labels.get(risk.treatment, risk.treatment),
            str(risk.plan_due_date) if risk.plan_due_date else "",
            plans_text,
            "Sì" if risk.risk_accepted_formally else (
                "In attesa" if risk.treatment == "accettare" else "No"
            ),
            _name(risk.risk_accepted_by),
            str(risk.risk_accepted_at.date()) if risk.risk_accepted_at else "",
            str(risk.risk_acceptance_expiry) if risk.risk_acceptance_expiry else "",
            risk.risk_acceptance_note,
            risk.impacted_systems,
            art21_map.get(risk.nis2_art21_category, ""),
            relevance_map.get(risk.nis2_relevance, ""),
            risk.critical_process.name if risk.critical_process else "",
            risk.plant.name if risk.plant else "",
            risk.status,
        ]

        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)\
              .alignment = Alignment(wrap_text=True, vertical="top")

        color = level_colors.get(risk.risk_level)
        if color:
            level_col = headers.index("Livello rischio") + 1
            ws.cell(row=row_idx, column=level_col).fill = PatternFill("solid", fgColor=color)

    col_widths = [
        35, 40, 40, 10, 22, 20, 22, 16, 16, 12, 16, 16, 12, 14, 14,
        12, 14, 50, 18, 20, 18, 16, 40, 35, 35, 22, 22, 20, 12,
    ]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Metodologia D-ITA-INF-23 — regole uniche di calcolo, governo e cicli.
# Ogni modulo che mostra o usa classi di rischio passa da queste funzioni.
# ─────────────────────────────────────────────────────────────────────────────

RISK_CLASSES = ("very_low", "low", "medium", "high", "critical")

# Matrice probabilità × impatto della procedura (§8): la classe si legge solo
# da qui, mai dal prodotto numerico. Costante: garantisce confrontabilità.
_MATRIX = {
    5: ("medium", "high", "high", "critical", "critical"),
    4: ("low", "medium", "high", "critical", "critical"),
    3: ("low", "medium", "medium", "high", "critical"),
    2: ("very_low", "low", "medium", "high", "high"),
    1: ("very_low", "low", "low", "medium", "high"),
}

IMPACT_DIMENSIONS = ("economic", "legal", "customer", "reputational", "people", "operational")

# Soglia minima d'impatto per perdita di riservatezza, dalla classe di
# protezione dell'informazione (§7.2, criterio del white paper VDA).
CONFIDENTIALITY_FLOOR = {"very_high": 5, "high": 4, "normal": 3, "low": 2}

# Regola di trattamento e scadenza per classe (§9.2).
TREATMENT_RULES = {
    "critical": {"rule": "mandatory", "months": 3},
    "high": {"rule": "evaluate", "months": 12},
    "medium": {"rule": "acceptable", "months": 24},
    "low": {"rule": "acceptable", "months": 60},
    "very_low": {"rule": "acceptable", "months": 60},
}


def risk_class(probability, impact) -> str | None:
    """Classe di rischio dalla matrice; None se manca uno dei due valori."""
    try:
        p, i = int(probability), int(impact)
    except (TypeError, ValueError):
        return None
    row = _MATRIX.get(p)
    if row is None or not 1 <= i <= 5:
        return None
    return row[i - 1]


def class_rank(cls: str | None) -> int:
    """Posizione della classe (0 = very_low … 4 = critical); -1 se assente."""
    return RISK_CLASSES.index(cls) if cls in RISK_CLASSES else -1


def shift_class(cls: str, delta: int, floor: str | None = None) -> str:
    """Override del Risk Owner (§8): sposta di `delta` livelli, mai sotto `floor`."""
    rank = max(0, min(len(RISK_CLASSES) - 1, class_rank(cls) + delta))
    if floor is not None:
        rank = max(rank, class_rank(floor))
    return RISK_CLASSES[rank]


def confidentiality_floor(levels) -> int | None:
    """Impatto minimo dato dalle classi di protezione delle informazioni colpite."""
    values = [CONFIDENTIALITY_FLOOR[lv] for lv in levels if lv in CONFIDENTIALITY_FLOOR]
    return max(values) if values else None


def overall_impact(dimensions: dict, floor: int | None = None) -> int | None:
    """Impatto finale = caso peggiore fra le dimensioni valorizzate e la soglia minima."""
    values = [int(v) for k, v in (dimensions or {}).items() if k in IMPACT_DIMENSIONS and v]
    if floor:
        values.append(int(floor))
    return max(values) if values else None


def risk_level_bucket(cls: str | None) -> str | None:
    """Semaforo verde/giallo/rosso per i moduli che non usano le 5 classi."""
    if cls in ("very_low", "low"):
        return "verde"
    if cls == "medium":
        return "giallo"
    if cls in ("high", "critical"):
        return "rosso"
    return None


def treatment_rule(cls: str | None) -> dict | None:
    return TREATMENT_RULES.get(cls)


# ── Policy di governo del rischio ────────────────────────────────────────────

DEFAULT_ECONOMIC_THRESHOLDS = {
    # Limite inferiore in euro di ciascun livello; sotto il livello 2 = livello 1.
    "5": 500000,
    "4": 250000,
    "3": 50000,
    "2": 10000,
}

_SITE_ACCEPT = {"roles": ["risk_owner"], "scope": "plant", "requires_body": False}

PRESETS = {
    "centralizzato": {
        "group_register_enabled": True,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": {**_SITE_ACCEPT, "notify": ["site_risk_manager"]},
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "org", "requires_body": True},
        },
        "upper_opinion": {"very_low": "none", "low": "none", "medium": "none",
                          "high": "binding", "critical": "binding"},
    },
    "federato": {
        "group_register_enabled": True,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": {**_SITE_ACCEPT, "notify": ["site_risk_manager"]},
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "plant", "requires_body": True},
        },
        "upper_opinion": {"very_low": "none", "low": "none", "medium": "none",
                          "high": "notify", "critical": "binding"},
    },
    "sito_singolo": {
        "group_register_enabled": False,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": _SITE_ACCEPT,
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "plant", "requires_body": True},
        },
        "upper_opinion": {c: "none" for c in RISK_CLASSES},
    },
}

_COMMON_DEFAULTS = {
    "acceptance_max_months": {"very_low": 12, "low": 12, "medium": 12, "high": 12, "critical": 6},
    "economic_thresholds": DEFAULT_ECONOMIC_THRESHOLDS,
    "overdue_escalation_days": 30,
    "review_frequency_months": 12,
}

OPINION_MODES = ("none", "notify", "binding")
_POLICY_DICT_FIELDS = ("acceptance_matrix", "upper_opinion", "acceptance_max_months", "economic_thresholds")
_POLICY_SCALAR_FIELDS = ("group_register_enabled", "overdue_escalation_days", "review_frequency_months")


def default_preset() -> str:
    """Senza policy: un solo sito attivo → sito singolo, altrimenti centralizzato."""
    from apps.plants.models import Plant

    return "centralizzato" if Plant.objects.filter(status="attivo").count() > 1 else "sito_singolo"


def preset_defaults(preset: str) -> dict:
    import copy

    base = copy.deepcopy(PRESETS[preset])
    base.update(copy.deepcopy(_COMMON_DEFAULTS))
    return base


def resolve_policy(plant=None) -> dict:
    """Policy effettiva per un registro: preset → organizzazione → sito.

    Per i campi dizionario (per classe o per livello) l'override è chiave per
    chiave; per gli scalari vale il valore più specifico non nullo.
    """
    from .models import RiskGovernancePolicy

    org = RiskGovernancePolicy.objects.filter(plant__isnull=True).first()
    site = (
        RiskGovernancePolicy.objects.filter(plant=plant).first()
        if plant is not None else None
    )
    preset = org.preset if org else default_preset()
    effective = preset_defaults(preset)
    for layer in (org, site):
        if layer is None:
            continue
        for field in _POLICY_DICT_FIELDS:
            override = getattr(layer, field) or {}
            effective[field] = {**effective[field], **override}
        for field in _POLICY_SCALAR_FIELDS:
            value = getattr(layer, field)
            if value is not None:
                effective[field] = value
    effective["preset"] = preset
    effective["configured"] = org is not None
    effective["org_policy_id"] = str(org.pk) if org else None
    effective["plant_policy_id"] = str(site.pk) if site else None
    return effective


def economic_level(amount, thresholds: dict) -> int:
    """Livello d'impatto economico (1–5) di un importo in euro."""
    for level in ("5", "4", "3", "2"):
        if amount >= thresholds[level]:
            return int(level)
    return 1


def _validate_policy_data(data: dict) -> None:
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    for field in ("acceptance_matrix", "upper_opinion", "acceptance_max_months"):
        unknown = set((data.get(field) or {})) - set(RISK_CLASSES)
        if unknown:
            raise ValidationError(_("Classi di rischio non valide: %(classes)s") % {"classes": ", ".join(sorted(unknown))})
    for mode in (data.get("upper_opinion") or {}).values():
        if mode not in OPINION_MODES:
            raise ValidationError(_("Modalità di parere non valida: %(mode)s") % {"mode": mode})
    for cls, rule in (data.get("acceptance_matrix") or {}).items():
        if not isinstance(rule, dict) or rule.get("scope") not in ("plant", "org"):
            raise ValidationError(_("Regola di accettazione non valida per la classe %(cls)s") % {"cls": cls})
    for months in (data.get("acceptance_max_months") or {}).values():
        if not isinstance(months, int) or months < 1:
            raise ValidationError(_("La validità dell'accettazione deve essere un numero di mesi positivo."))
    thresholds = data.get("economic_thresholds") or {}
    if thresholds:
        if set(thresholds) != {"2", "3", "4", "5"}:
            raise ValidationError(_("Le soglie economiche richiedono i livelli 2, 3, 4 e 5."))
        values = [thresholds[k] for k in ("2", "3", "4", "5")]
        if any(not isinstance(v, (int, float)) or v <= 0 for v in values) or values != sorted(set(values)):
            raise ValidationError(_("Le soglie economiche devono essere positive e crescenti dal livello 2 al 5."))


def save_governance_policy(user, plant, data: dict):
    """Crea o aggiorna la policy di un perimetro (organizzazione o sito).

    Le regole di governo le decide chi ha scope di organizzazione, anche le
    eccezioni per un singolo sito (procedura §1: la capogruppo approva).
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from rest_framework.exceptions import PermissionDenied

    from core.audit import log_action
    from core.scoping import user_has_org_scope

    from .models import RiskGovernancePolicy

    if not user_has_org_scope(user):
        raise PermissionDenied(_("Solo chi ha accesso a tutta l'organizzazione può modificare il governo del rischio."))
    if "preset" in data and data["preset"] not in PRESETS:
        raise ValidationError(_("Preset non valido."))
    if plant is not None and "preset" in data:
        raise ValidationError(_("Il preset si sceglie solo a livello di organizzazione."))
    _validate_policy_data(data)

    allowed = set(_POLICY_DICT_FIELDS) | set(_POLICY_SCALAR_FIELDS) | {"preset", "notes"}
    with transaction.atomic():
        policy = RiskGovernancePolicy.objects.filter(plant=plant).first()
        created = policy is None
        if created:
            policy = RiskGovernancePolicy(plant=plant, created_by=user)
        for key, value in data.items():
            if key in allowed:
                setattr(policy, key, value)
        policy.approved_by = user
        policy.approved_at = timezone.now()
        policy.save()
        log_action(
            user=user,
            action_code="risk.policy.updated",
            level="L1",
            entity=policy,
            payload={
                "plant_id": str(plant.pk) if plant else None,
                "created": created,
                "fields": sorted(k for k in data if k in allowed),
            },
        )
    return policy


# ── Catalogo minacce ─────────────────────────────────────────────────────────

_THREAT_CODE_RE = r"^[A-Z0-9_]{2,30}$"


def _validate_threat_fields(asset_types, cia) -> None:
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from .models import ASSET_TYPES

    if not asset_types or set(asset_types) - set(ASSET_TYPES):
        raise ValidationError(_("Tipologie di asset non valide."))
    if set(cia or []) - {"C", "I", "A"}:
        raise ValidationError(_("Le proprietà colpite possono essere solo C, I, A."))


def sync_threat_catalog(data: dict) -> dict:
    """Allinea le voci `source=catalog` al file JSON del catalogo.

    Upsert per codice; le voci sparite dal file vengono disattivate (i rischi
    le referenziano). Le voci personalizzate non vengono toccate: se un codice
    del file coincide con una voce custom, la voce custom resta e il codice del
    file viene segnalato come conflitto.
    """
    from .models import ThreatCatalogEntry

    version = str(data.get("version", ""))
    counts = {"created": 0, "updated": 0, "deactivated": 0, "conflicts": []}
    seen = set()
    with transaction.atomic():
        for item in data.get("threats", []):
            code = item["code"]
            seen.add(code)
            _validate_threat_fields(item.get("asset_types"), item.get("cia"))
            entry = ThreatCatalogEntry.objects.filter(code=code).first()
            if entry and entry.source == "custom":
                counts["conflicts"].append(code)
                continue
            values = {
                "asset_types": item["asset_types"],
                "cia": item.get("cia", []),
                "translations": item.get("translations", {}),
                "source": "catalog",
                "catalog_version": version,
                "active": True,
            }
            if entry is None:
                ThreatCatalogEntry.objects.create(code=code, **values)
                counts["created"] += 1
            else:
                for key, value in values.items():
                    setattr(entry, key, value)
                entry.save()
                counts["updated"] += 1
        counts["deactivated"] = (
            ThreatCatalogEntry.objects.filter(source="catalog", active=True)
            .exclude(code__in=seen)
            .update(active=False)
        )
    return counts


def _require_org_scope_for_catalog(user) -> None:
    from django.utils.translation import gettext as _
    from rest_framework.exceptions import PermissionDenied

    from core.scoping import user_has_org_scope

    if not user_has_org_scope(user):
        raise PermissionDenied(_("Solo chi ha accesso a tutta l'organizzazione può gestire il catalogo minacce."))


def create_custom_threat(user, *, code, asset_types, cia, translations):
    import re

    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    from .models import ThreatCatalogEntry

    _require_org_scope_for_catalog(user)
    code = (code or "").strip().upper()
    if not re.match(_THREAT_CODE_RE, code):
        raise ValidationError(_("Il codice deve avere da 2 a 30 caratteri fra lettere maiuscole, cifre e trattino basso."))
    if ThreatCatalogEntry.objects.filter(code=code).exists():
        raise ValidationError(_("Esiste già una minaccia con questo codice."))
    _validate_threat_fields(asset_types, cia)
    if not any((v or {}).get("title") for v in (translations or {}).values()):
        raise ValidationError(_("Indica almeno il titolo della minaccia."))
    with transaction.atomic():
        entry = ThreatCatalogEntry.objects.create(
            code=code, asset_types=asset_types, cia=cia or [], translations=translations,
            source="custom", created_by=user,
        )
        log_action(user=user, action_code="risk.catalog.custom_created", level="L2",
                   entity=entry, payload={"code": code})
    return entry


def update_custom_threat(user, entry, **fields):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_org_scope_for_catalog(user)
    if entry.source != "custom":
        raise ValidationError(_("Le voci del catalogo di gruppo non si modificano da qui."))
    asset_types = fields.get("asset_types", entry.asset_types)
    cia = fields.get("cia", entry.cia)
    _validate_threat_fields(asset_types, cia)
    with transaction.atomic():
        for key in ("asset_types", "cia", "translations", "active"):
            if key in fields:
                setattr(entry, key, fields[key])
        entry.save()
        log_action(user=user, action_code="risk.catalog.custom_updated", level="L2",
                   entity=entry, payload={"code": entry.code, "fields": sorted(fields)})
    return entry


def deactivate_threat(user, entry):
    """Disattiva una voce personalizzata (i rischi già valutati la conservano)."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_org_scope_for_catalog(user)
    if entry.source != "custom":
        raise ValidationError(_("Le voci del catalogo di gruppo non si disattivano da qui."))
    with transaction.atomic():
        entry.active = False
        entry.save(update_fields=["active", "updated_at"])
        log_action(user=user, action_code="risk.catalog.custom_deactivated", level="L2",
                   entity=entry, payload={"code": entry.code})
    return entry


# ── Perimetro della valutazione ──────────────────────────────────────────────

def plant_handles_prototypes(plant) -> bool:
    """Un sito gestisce prototipi se ha attivo il framework TISAX prototipi."""
    from apps.plants.models import PlantFramework

    if plant is None:
        return False
    return PlantFramework.objects.filter(
        plant=plant, framework__code="TISAX_PROTO", active=True,
    ).exists()


def asset_types_present(plant) -> list:
    """Tipologie di asset da coprire nel registro (procedura §6.5).

    Sito: IT, Sede e Personale sempre; OT se il sito ha OT; Fornitori se ha
    fornitori attivi; Prototipi se gestisce prototipi. Gruppo: IT, Personale e
    Fornitori (servizi condivisi, strutture e contratti della capogruppo).
    """
    from apps.assets.models import Asset
    from apps.suppliers.models import Supplier

    if plant is None:
        return ["IT", "PERSONALE", "FORNITORI"]
    types = ["IT"]
    if plant.has_ot or Asset.objects.filter(plant=plant, asset_type="OT").exists():
        types.append("OT")
    types += ["SEDE", "PERSONALE"]
    if Supplier.objects.filter(plants=plant, status="attivo").exists():
        types.append("FORNITORI")
    if plant_handles_prototypes(plant):
        types.append("PROTOTIPI")
    return types


# ── Cicli di valutazione ─────────────────────────────────────────────────────

def open_cycle(plant=None):
    """Ciclo in corso o in approvazione del registro (sito o gruppo), se c'è."""
    from .models import RiskAssessmentCycle

    return RiskAssessmentCycle.objects.filter(
        plant=plant, status__in=RiskAssessmentCycle.OPEN_STATUSES,
    ).first()


def approved_cycle(plant=None):
    """Ultimo ciclo approvato del registro: è la valutazione vigente."""
    from .models import RiskAssessmentCycle

    return (
        RiskAssessmentCycle.objects.filter(plant=plant, status="approvato")
        .order_by("-approved_at", "-started_at").first()
    )


def start_cycle(user, plant, kind: str, trigger_reason: str = ""):
    """Avvia una valutazione del registro di un sito (o del gruppo se plant è None).

    - `primo`: solo se il registro non ha ancora valutazioni con il metodo
      attuale (i cicli `legacy` non contano);
    - `periodico` / `straordinario`: richiedono una valutazione approvata;
      lo straordinario richiede il motivo (trigger, §11.2).
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from core.scoping import require_org_scope_for_org_wide, require_plant_access

    from .models import RiskAssessmentCycle

    if kind not in ("primo", "periodico", "straordinario"):
        raise ValidationError(_("Tipo di valutazione non valido."))
    if plant is None:
        require_org_scope_for_org_wide(user, None)
        if not resolve_policy(None)["group_register_enabled"]:
            raise ValidationError(_("Il registro di gruppo non è attivo nella policy di governo del rischio."))
    else:
        require_plant_access(user, plant)
    if open_cycle(plant):
        raise ValidationError(_("C'è già una valutazione aperta per questo registro."))
    current_method = RiskAssessmentCycle.objects.filter(plant=plant).exclude(kind="legacy")
    if kind == "primo" and current_method.exists():
        raise ValidationError(_("Il primo risk assessment è già stato avviato per questo registro."))
    if kind != "primo" and not current_method.filter(status__in=("approvato", "archiviato")).exists():
        raise ValidationError(_("Serve una valutazione approvata prima di una revisione."))
    if kind == "straordinario" and not (trigger_reason or "").strip():
        raise ValidationError(_("Indica il motivo della revisione straordinaria."))

    with transaction.atomic():
        cycle = RiskAssessmentCycle.objects.create(
            plant=plant, kind=kind, trigger_reason=(trigger_reason or "").strip(),
            status="in_corso", started_at=timezone.now(), created_by=user,
        )
        log_action(
            user=user, action_code="risk.cycle.started", level="L1", entity=cycle,
            payload={"plant_id": str(plant.pk) if plant else None, "kind": kind},
        )
    return cycle
