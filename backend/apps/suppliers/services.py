import datetime
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Supplier,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
    SupplierQuestionnaire,
)


def get_expiring_contracts(days: int = 60):
    """Return suppliers whose evaluation_date expires within the given number of days."""
    today = timezone.localdate()
    deadline = today + datetime.timedelta(days=days)
    return Supplier.objects.filter(
        status="attivo",
        evaluation_date__isnull=False,
        evaluation_date__lte=deadline,
        evaluation_date__gte=today,
    )


def get_high_risk_suppliers():
    """Return suppliers with risk_level alto or critico."""
    return Supplier.objects.filter(risk_level__in=["alto", "critico"], status="attivo")


# Soglia TPRM (Supplier.concentration_threshold) → livello di rischio del registro.
_CONCENTRATION_SEVERITY = {"media": "medio", "critica": "alto"}
_RISK_ORDER = ("basso", "medio", "alto", "critico")
_RISK_RANK = {c: i for i, c in enumerate(_RISK_ORDER)}


def get_concentration_risk_register(suppliers_qs=None) -> dict:
    """Registro rischi di concentrazione della fornitura (P2-4 — catena fornitura→risk).

    Trasforma il campo finora inerte `Supplier.supply_concentration_pct` in un
    elenco di rischi consultabile dal risk manager. Ogni fornitore attivo con
    concentrazione **media** o **critica** diventa una voce di rischio con
    livello derivato dalla soglia TPRM (media→medio, critica→alto) e con un
    **bump di un livello** se il fornitore è NIS2-relevant (dipendenza critica
    su un'entità essenziale/importante). I fornitori con concentrazione bassa o
    non valorizzata non sono rischi di concentrazione.

    `suppliers_qs` permette al chiamante (es. viewset) di passare un queryset
    già filtrato per scope-plant; il filtro `status="attivo"` e l'esclusione dei
    soft-deleted sono applicati comunque.

    Rationale: ACN Delibera 127434 (soglie concentrazione); NIS2 Art. 21.2(d)
    supply chain risk management; ISO 27001 A.5.19-A.5.22.
    """
    if suppliers_qs is None:
        suppliers_qs = Supplier.objects.all()
    suppliers_qs = suppliers_qs.filter(
        status="attivo",
        deleted_at__isnull=True,
        supply_concentration_pct__isnull=False,
    ).prefetch_related("plants")

    items: list[dict] = []
    by_level = {"medio": 0, "alto": 0, "critico": 0}
    for sup in suppliers_qs:
        threshold = sup.concentration_threshold
        base = _CONCENTRATION_SEVERITY.get(threshold)
        if base is None:
            continue  # bassa / nd → non è un rischio di concentrazione
        rank = _RISK_RANK[base]
        if sup.nis2_relevant:
            rank = min(rank + 1, len(_RISK_ORDER) - 1)
        risk_level = _RISK_ORDER[rank]
        by_level[risk_level] = by_level.get(risk_level, 0) + 1
        items.append({
            "supplier_id": str(sup.id),
            "supplier_name": sup.name,
            "concentration_pct": float(sup.supply_concentration_pct),
            "threshold": threshold,
            "nis2_relevant": sup.nis2_relevant,
            "risk_level": risk_level,
            "plants": [p.name for p in sup.plants.all()],
        })

    items.sort(key=lambda x: (-_RISK_RANK[x["risk_level"]], -x["concentration_pct"]))
    return {
        "items": items,
        "count": len(items),
        "by_level": by_level,
        "attention": by_level.get("alto", 0) + by_level.get("critico", 0),
    }


def check_concentration_crossing(supplier: Supplier, user=None) -> bool:
    """Notifica M19 quando un fornitore *attraversa* la soglia di concentrazione critica.

    Anti-spam: la notifica parte solo alla **transizione** verso `critica` (la
    soglia precedentemente notificata non era già `critica`). Se la concentrazione
    rientra sotto `critica`, azzera il marcatore così un futuro ri-attraversamento
    notifica di nuovo. Best-effort: un fallimento dell'invio non blocca il salvataggio
    del fornitore. Ritorna True se una notifica è stata inviata.

    Va chiamata dopo che `supply_concentration_pct` è stato salvato (es. dal
    viewset su create/update).
    """
    threshold = supplier.concentration_threshold  # 'bassa'|'media'|'critica'|'nd'
    last = supplier.concentration_notified_threshold or ""

    if threshold != "critica":
        # Rientrata o mai critica: resetta il marcatore se necessario (consente
        # una nuova notifica al prossimo attraversamento).
        if last:
            supplier.concentration_notified_threshold = ""
            supplier.save(update_fields=["concentration_notified_threshold", "updated_at"])
        return False

    if last == "critica":
        return False  # già notificata, niente spam

    # Transizione verso 'critica' → notifica + memorizza il marcatore.
    supplier.concentration_notified_threshold = "critica"
    supplier.save(update_fields=["concentration_notified_threshold", "updated_at"])

    from core.audit import log_action
    try:
        log_action(
            user=user,
            action_code="suppliers.concentration.critical",
            level="L2",
            entity=supplier,
            payload={
                "supplier_id": str(supplier.id),
                "concentration_pct": float(supplier.supply_concentration_pct or 0),
                "nis2_relevant": supplier.nis2_relevant,
            },
        )
    except Exception as exc:  # pragma: no cover - audit best-effort
        logging.getLogger(__name__).warning("suppliers: audit concentration crossing non scritto: %s", exc)

    sent = False
    try:
        from apps.notifications.resolver import fire_notification
        fire_notification(
            "supplier_concentration_critical",
            plant=supplier.plants.first(),
            context={"supplier": supplier},
        )
        sent = True
    except Exception as exc:  # noqa: BLE001 - notifica best-effort
        logging.getLogger(__name__).warning(
            "suppliers: notifica concentration crossing non inviata (%s): %s", supplier.id, exc,
        )
    return sent


PARAMETER_KEYS = ("impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance")


def _compute_weighted_score(scores: dict, weights: dict) -> float:
    """Calcola weighted_score = Σ score_i × weight_i. Restituisce float arrotondato a 3 decimali."""
    total = 0.0
    for key in PARAMETER_KEYS:
        score = float(scores[key])
        weight = float(weights[key])
        total += score * weight
    return round(total, 3)


@transaction.atomic
def create_internal_evaluation(
    supplier: Supplier,
    scores: dict,
    user,
    notes: str = "",
) -> SupplierInternalEvaluation:
    """
    Crea una nuova valutazione interna del rischio fornitore.

    - `scores`: dict con chiavi PARAMETER_KEYS, valori 1–5.
    - Marca la precedente valutazione corrente come is_current=False (storico).
    - Calcola weighted_score con i pesi correnti di SupplierEvaluationConfig.
    - Classifica con le soglie correnti.
    - Aggiorna Supplier.internal_risk_level e ricalcola Supplier.risk_adj.
    - Emette audit log L2.
    """
    from django.core.exceptions import ValidationError
    from core.audit import log_action

    missing = [k for k in PARAMETER_KEYS if k not in scores]
    if missing:
        raise ValidationError(f"Score mancanti: {missing}")
    for k in PARAMETER_KEYS:
        v = scores[k]
        if not isinstance(v, int) or not (1 <= v <= 5):
            raise ValidationError(f"Score '{k}' deve essere intero 1–5 (ricevuto: {v!r}).")

    config = SupplierEvaluationConfig.get_solo()
    weighted = _compute_weighted_score(scores, config.weights)
    risk_class = config.classify(weighted)

    SupplierInternalEvaluation.objects.filter(
        supplier=supplier, is_current=True, deleted_at__isnull=True
    ).update(is_current=False)

    evaluation = SupplierInternalEvaluation.objects.create(
        supplier=supplier,
        score_impatto=scores["impatto"],
        score_accesso=scores["accesso"],
        score_dati=scores["dati"],
        score_dipendenza=scores["dipendenza"],
        score_integrazione=scores["integrazione"],
        score_compliance=scores["compliance"],
        weighted_score=Decimal(str(weighted)),
        risk_class=risk_class,
        weights_snapshot=dict(config.weights),
        thresholds_snapshot=dict(config.risk_thresholds),
        is_current=True,
        evaluated_by=user,
        notes=notes,
        created_by=user,
    )

    # Hook Fase 3 — aggiornamento internal_risk_level + ricalcolo risk_adj
    try:
        from .risk_adj import recompute_risk_adj
        recompute_risk_adj(supplier)
    except ImportError:
        pass

    log_action(
        user=user,
        action_code="suppliers.internal_evaluation.create",
        level="L2",
        entity=evaluation,
        payload={
            "supplier_id": str(supplier.id),
            "supplier_name": supplier.name,
            "scores": {k: scores[k] for k in PARAMETER_KEYS},
            "weighted_score": weighted,
            "risk_class": risk_class,
        },
    )
    return evaluation


def complete_assessment(
    assessment,
    user,
    score_overall=None,
    score_governance=None,
    score_security=None,
    score_bcp=None,
    findings: str = "",
    next_assessment_months: int = 12,
):
    from core.audit import log_action
    from apps.compliance_schedule.services import get_due_date

    assessment.status = "completato"
    assessment.assessed_by = user
    assessment.assessment_date = timezone.localdate()
    assessment.score = score_overall
    assessment.score_overall = score_overall
    assessment.score_governance = score_governance
    assessment.score_security = score_security
    assessment.score_bcp = score_bcp
    assessment.findings = findings
    assessment.next_assessment_date = get_due_date(
        "supplier_assessment",
        plant=assessment.supplier.plants.first(),
    )
    assessment.save()

    if score_overall is not None:
        supplier = assessment.supplier
        if score_overall >= 75:
            supplier.risk_level = "basso"
        elif score_overall >= 50:
            supplier.risk_level = "medio"
        else:
            supplier.risk_level = "alto"
        supplier.save(update_fields=["risk_level", "updated_at"])

    log_action(
        user=user,
        action_code="supplier.assessment.completed",
        level="L2",
        entity=assessment,
        payload={
            "score_overall": score_overall,
            "risk_level": assessment.computed_risk_level,
        },
    )

    try:
        from apps.notifications.resolver import fire_notification
        fire_notification(
            "supplier_assessment",
            plant=assessment.supplier.plants.first(),
            context={"assessment": assessment},
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("suppliers: notifica assessment non inviata: %s", exc)
    return assessment


def approve_assessment(assessment, user, notes: str = ""):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if assessment.status != "completato":
        raise ValidationError(_("Solo assessment completati possono essere approvati."))

    assessment.status = "approvato"
    assessment.reviewed_by = user
    assessment.reviewed_at = timezone.now()
    assessment.review_notes = notes
    assessment.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_notes", "updated_at",
        ]
    )

    # Ricalcolo risk_adj — l'audit terze parti approvato partecipa al worst-case
    from .risk_adj import recompute_risk_adj
    recompute_risk_adj(assessment.supplier)

    log_action(
        user=user,
        action_code="supplier.assessment.approved",
        level="L1",
        entity=assessment,
        payload={"notes": notes[:100]},
    )
    return assessment


def reject_assessment(assessment, user, notes: str = ""):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if not notes or len(notes.strip()) < 10:
        raise ValidationError(_("Motivazione rifiuto obbligatoria (min 10 caratteri)."))

    assessment.status = "rifiutato"
    assessment.reviewed_by = user
    assessment.reviewed_at = timezone.now()
    assessment.review_notes = notes
    assessment.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_notes", "updated_at",
        ]
    )

    log_action(
        user=user,
        action_code="supplier.assessment.rejected",
        level="L1",
        entity=assessment,
        payload={"notes": notes[:200]},
    )
    return assessment


# ── Questionnaire services ──────────────────────────────────────────────────


def _build_email_body(template, supplier) -> tuple[str, str]:
    """Interpolate template variables. Returns (subject, body)."""
    subject = template.subject.replace("{supplier_name}", supplier.name)
    body = template.body.replace("{supplier_name}", supplier.name).replace(
        "{questionnaire_link}", template.form_url
    )
    return subject, body


def send_questionnaire(supplier, template, user) -> "SupplierQuestionnaire":
    """
    First send of a questionnaire to a supplier.
    Creates SupplierQuestionnaire record and sends email.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action
    from apps.notifications.services import send_grc_email

    if not supplier.email:
        raise ValidationError(_("Nessun indirizzo email configurato per questo fornitore."))

    now = timezone.now()
    subject, body = _build_email_body(template, supplier)
    cc_emails = [e for e in (supplier.additional_emails or []) if e]

    questionnaire = SupplierQuestionnaire(
        supplier=supplier,
        template=template,
        subject_snapshot=subject,
        body_snapshot=body,
        form_url_snapshot=template.form_url,
        sent_at=now,
        last_sent_at=now,
        sent_to=supplier.email,
        sent_cc_snapshot=cc_emails,
        sent_by=user,
        send_count=1,
        status="inviato",
        created_by=user,
    )
    questionnaire.save()

    send_grc_email(
        subject=subject,
        body=body,
        recipients=[supplier.email],
        cc=cc_emails,
    )

    log_action(
        user=user,
        action_code="supplier.questionnaire.sent",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": supplier.name,
            "sent_to": supplier.email,
            "sent_cc_count": len(cc_emails),
            "template": template.name,
            "send_count": 1,
        },
    )
    return questionnaire


def resend_questionnaire(questionnaire, user) -> "SupplierQuestionnaire":
    """
    Resend an existing questionnaire (follow-up). Increments send_count.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action
    from apps.notifications.services import send_grc_email

    if questionnaire.status == "risposto":
        raise ValidationError(_("Il questionario ha già ricevuto risposta."))

    now = timezone.now()
    questionnaire.send_count += 1
    questionnaire.last_sent_at = now
    if questionnaire.send_count >= 3:
        questionnaire.status = "inviato"  # keep as inviato but send_count signals 3rd strike
    # Aggiorna lo snapshot CC con la lista corrente del fornitore (i contatti
    # potrebbero essere cambiati tra il primo invio e il follow-up).
    cc_emails = [e for e in (questionnaire.supplier.additional_emails or []) if e]
    questionnaire.sent_cc_snapshot = cc_emails
    questionnaire.save(
        update_fields=[
            "send_count", "last_sent_at", "status",
            "sent_cc_snapshot", "updated_at",
        ],
    )

    send_grc_email(
        subject=questionnaire.subject_snapshot,
        body=questionnaire.body_snapshot,
        recipients=[questionnaire.sent_to],
        cc=cc_emails,
    )

    log_action(
        user=user,
        action_code="supplier.questionnaire.resent",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": questionnaire.supplier.name,
            "sent_to": questionnaire.sent_to,
            "sent_cc_count": len(cc_emails),
            "send_count": questionnaire.send_count,
        },
    )
    return questionnaire


def register_evaluation(questionnaire, evaluation_date, risk_result, user, notes: str = "") -> "SupplierQuestionnaire":
    """
    Record the received evaluation: sets evaluation_date, risk_result, expires_at.
    expires_at = evaluation_date + questionnaire_validity_months (da SupplierEvaluationConfig).
    Updates supplier.risk_level and supplier.evaluation_date.
    """
    from core.audit import log_action

    config = SupplierEvaluationConfig.get_solo()
    expires_at = evaluation_date + datetime.timedelta(days=config.questionnaire_validity_months * 30)

    questionnaire.evaluation_date = evaluation_date
    questionnaire.risk_result = risk_result
    questionnaire.status = "risposto"
    questionnaire.expires_at = expires_at
    if notes:
        questionnaire.notes = notes
    questionnaire.save(
        update_fields=[
            "evaluation_date", "risk_result", "status", "expires_at", "notes", "updated_at"
        ]
    )

    # Update supplier
    supplier = questionnaire.supplier
    supplier.risk_level = risk_result
    supplier.evaluation_date = evaluation_date
    supplier.save(update_fields=["risk_level", "evaluation_date", "updated_at"])

    # Ricalcolo risk_adj — il questionario valutato contribuisce al worst-case
    from .risk_adj import recompute_risk_adj
    recompute_risk_adj(supplier)

    log_action(
        user=user,
        action_code="supplier.questionnaire.evaluated",
        level="L2",
        entity=questionnaire,
        payload={
            "supplier": supplier.name,
            "evaluation_date": str(evaluation_date),
            "risk_result": risk_result,
            "expires_at": str(expires_at),
        },
    )
    return questionnaire


def check_questionnaire_followups():
    """
    Check questionnaires awaiting response for > 7 days since last send.

    Invia **una sola email di riepilogo per operatore** (`sent_by`) con tutti i
    fornitori che non hanno risposto, invece di una mail per questionario (che,
    girando settimanalmente, generava spam quando i pendenti erano molti).
    """
    from collections import defaultdict

    from apps.notifications.services import send_grc_email

    today = timezone.localdate()
    threshold = timezone.now() - datetime.timedelta(days=7)

    pending = SupplierQuestionnaire.objects.filter(
        status="inviato",
        evaluation_date__isnull=True,
        last_sent_at__lt=threshold,
        deleted_at__isnull=True,
    ).select_related("supplier", "sent_by")

    # Raggruppa per operatore (chi ha inviato il questionario). Saltiamo i
    # questionari senza operatore o senza email: non c'e' destinatario.
    by_operator = defaultdict(list)
    for q in pending:
        operator_email = q.sent_by.email if q.sent_by and q.sent_by.email else None
        if not operator_email:
            continue
        by_operator[operator_email].append(q)

    def _days(q):
        return (today - q.last_sent_at.date()).days

    for operator_email, questionnaires in by_operator.items():
        # 3+ tentativi prima (piu' urgenti), poi i follow-up; entro ogni gruppo
        # i piu' vecchi (last_sent_at) in cima.
        three_strike = sorted(
            (q for q in questionnaires if q.send_count >= 3), key=lambda q: q.last_sent_at
        )
        followups = sorted(
            (q for q in questionnaires if q.send_count < 3), key=lambda q: q.last_sent_at
        )

        lines = []
        if three_strike:
            lines.append("\U0001f534 3+ tentativi senza risposta - contatto diretto necessario:")
            for q in three_strike:
                lines.append(
                    f"  - {q.supplier.name} ({q.sent_to}): "
                    f"{q.send_count} invii, {_days(q)} giorni dall'ultimo"
                )
            lines.append("")
        if followups:
            lines.append("Follow-up - promemoria da inviare:")
            for q in followups:
                lines.append(
                    f"  - {q.supplier.name} ({q.sent_to}): "
                    f"{_days(q)} giorni senza risposta (invio {q.send_count}, prossimo {q.send_count + 1})"
                )
            lines.append("")

        lines.append("Accedi al modulo Fornitori per inviare i promemoria o aggiornare lo stato.")

        total = len(questionnaires)
        plural = "e" if total == 1 else "i"
        subject = f"[GRC] Riepilogo questionari fornitori senza risposta ({total} fornitor{plural})"
        send_grc_email(subject=subject, body="\n".join(lines), recipients=[operator_email])
