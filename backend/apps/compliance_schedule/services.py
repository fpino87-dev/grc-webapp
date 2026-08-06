"""
Central service for compliance deadlines and activity schedule.

get_due_date(rule_type, plant, from_date) — single entry point for all modules.
get_activity_schedule(plant, months_ahead) — aggregates expiring activities.
get_required_documents_status(plant, framework) — traffic-light for required docs.
"""
from __future__ import annotations

import datetime
import logging
from typing import Optional

from .models import (
    ComplianceSchedulePolicy,
    DEFAULT_RULES,
    RULE_TYPE_LABELS,
)

logger = logging.getLogger(__name__)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_active_policy(plant) -> Optional[ComplianceSchedulePolicy]:
    """Return the active policy for a plant, falling back to global."""
    if plant:
        p = ComplianceSchedulePolicy.objects.filter(plant=plant, is_active=True).first()
        if p:
            return p
    return ComplianceSchedulePolicy.objects.filter(plant__isnull=True, is_active=True).first()


def _get_rule(rule_type: str, plant) -> tuple[int, str, int]:
    """Return (frequency_value, frequency_unit, alert_days_before) from active policy or defaults."""
    policy = _get_active_policy(plant)
    if policy:
        rule = policy.rules.filter(rule_type=rule_type, enabled=True).first()
        if rule:
            return rule.frequency_value, rule.frequency_unit, rule.alert_days_before
    defaults = DEFAULT_RULES.get(rule_type)
    if defaults:
        return defaults
    return 365, "days", 30  # fallback: 1 year


def _add_duration(base: datetime.date, value: int, unit: str) -> datetime.date:
    if unit == "days":
        return base + datetime.timedelta(days=value)
    elif unit == "weeks":
        return base + datetime.timedelta(weeks=value)
    elif unit == "months":
        month = base.month - 1 + value
        year = base.year + month // 12
        month = month % 12 + 1
        day = min(base.day, [31,28,29,31,30,31,30,31,31,30,31,30,31][month])
        return datetime.date(year, month, day)
    elif unit == "years":
        try:
            return base.replace(year=base.year + value)
        except ValueError:
            return base.replace(year=base.year + value, day=28)
    return base + datetime.timedelta(days=value * 30)


# ─── Public API ───────────────────────────────────────────────────────────────

def get_due_date(rule_type: str, plant=None, from_date: Optional[datetime.date] = None) -> datetime.date:
    """Compute the next due date for rule_type starting from from_date (default: today in the plant's timezone)."""
    from apps.plants.services import plant_today

    freq_val, freq_unit, _ = _get_rule(rule_type, plant)
    base = from_date or plant_today(plant)
    return _add_duration(base, freq_val, freq_unit)


def get_alert_threshold(rule_type: str, plant=None) -> int:
    """Return how many days before due date an alert should fire."""
    _, _, alert_days = _get_rule(rule_type, plant)
    return alert_days


def create_default_policy(plant=None, name: str = "Policy predefinita") -> ComplianceSchedulePolicy:
    """Create a ComplianceSchedulePolicy with all DEFAULT_RULES as ScheduleRule rows."""
    from .models import ScheduleRule
    from django.utils import timezone as tz

    policy = ComplianceSchedulePolicy.objects.create(
        plant=plant,
        name=name,
        is_active=True,
        valid_from=tz.now().date(),
    )
    rules = [
        ScheduleRule(
            policy=policy,
            rule_type=rule_type,
            frequency_value=freq_val,
            frequency_unit=freq_unit,
            alert_days_before=alert_days,
        )
        for rule_type, (freq_val, freq_unit, alert_days) in DEFAULT_RULES.items()
    ]
    ScheduleRule.objects.bulk_create(rules)
    return policy


# ─── Activity Schedule ────────────────────────────────────────────────────────

def get_activity_schedule(plant=None, months_ahead: int = 6) -> list[dict]:
    """
    Aggregate all upcoming expiring activities across GRC modules.
    Returns a list of dicts sorted by due_date ascending.

    "Oggi" è la data nel fuso orario del sito (F3): per un plant a Istanbul
    o New York la finestra scaduto/in-scadenza segue la mezzanotte locale,
    non quella del server.
    """
    from apps.plants.services import plant_today

    today = plant_today(plant)
    cutoff = _add_duration(today, months_ahead, "months")
    activities = []

    # Helper
    def _add(category: str, label: str, due: datetime.date | None, status: str = "ok", ref_id: str = "", url: str = ""):
        if due and today <= due <= cutoff:
            days_left = (due - today).days
            alert_days = get_alert_threshold(category, plant)
            urgency = "red" if days_left <= 7 else ("yellow" if days_left <= alert_days else "green")
            activities.append({
                "category": category,
                "category_label": RULE_TYPE_LABELS.get(category, category),
                "label": label,
                "due_date": str(due),
                "days_left": days_left,
                "urgency": urgency,
                "status": status,
                "ref_id": ref_id,
                "url": url,
            })

    plant_filter = {"plant": plant} if plant else {}

    # Documents expiring
    try:
        from apps.documents.models import Document

        doc_qs = Document.objects.filter(
            deleted_at__isnull=True,
            review_due_date__isnull=False,
        )
        if plant:
            doc_qs = doc_qs.filter(plant=plant)
        for doc in doc_qs:
            rule = (
                f"document_{doc.document_type}"
                if f"document_{doc.document_type}" in DEFAULT_RULES
                else "document_policy"
            )
            _add(rule, f"Doc: {doc.title}", doc.review_due_date, doc.status, str(doc.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze documenti", exc_info=True)

    # Evidences expiring
    try:
        from apps.documents.models import Evidence

        ev_qs = Evidence.objects.filter(valid_until__isnull=False)
        if plant:
            ev_qs = ev_qs.filter(control_instances__plant=plant).distinct()
        for ev in ev_qs:
            _add("control_review", f"Evidenza: {ev.title}", ev.valid_until, "active", str(ev.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze evidenze", exc_info=True)

    # Risk assessments — next review due
    try:
        from apps.risk.models import RiskAssessment

        risk_qs = RiskAssessment.objects.filter(status="completato", assessed_at__isnull=False)
        if plant:
            risk_qs = risk_qs.filter(**plant_filter)
        freq_val, freq_unit, _ = _get_rule("risk_assessment", plant)
        for ra in risk_qs:
            next_due = _add_duration(ra.assessed_at.date(), freq_val, freq_unit)
            _add("risk_assessment", f"Rischio: {ra.name}", next_due, ra.status, str(ra.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze risk assessment", exc_info=True)

    # BCP plans — next test date
    try:
        from apps.bcp.models import BcpPlan

        bcp_qs = BcpPlan.objects.filter(next_test_date__isnull=False)
        if plant:
            bcp_qs = bcp_qs.filter(**plant_filter)
        for plan in bcp_qs:
            _add("bcp_test", f"BCP Test: {plan.title}", plan.next_test_date, plan.status, str(plan.id))
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze BCP", exc_info=True)

    # Supplier assessments
    try:
        from apps.suppliers.models import SupplierAssessment

        sa_qs = SupplierAssessment.objects.filter(next_assessment_date__isnull=False)
        if plant:
            # Supplier ha una M2M `plants` (non un FK `plant`).
            sa_qs = sa_qs.filter(supplier__plants=plant).distinct()
        for sa in sa_qs:
            _add(
                "supplier_assessment",
                f"Fornitore: {sa.supplier.name}",
                sa.next_assessment_date,
                sa.status,
                str(sa.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze assessment fornitori", exc_info=True)

    # Supplier contracts expiring
    try:
        from apps.suppliers.models import Supplier

        sup_qs = Supplier.objects.filter(evaluation_date__isnull=False, deleted_at__isnull=True)
        if plant:
            # Supplier ha una M2M `plants` (non il FK `plant` di plant_filter).
            sup_qs = sup_qs.filter(plants=plant).distinct()
        for sup in sup_qs:
            _add(
                "supplier_contract_review",
                f"Contratto: {sup.name}",
                sup.evaluation_date,
                sup.status,
                str(sup.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze contratti fornitori", exc_info=True)

    # Training courses deadline
    try:
        from apps.training.models import TrainingCourse

        tr_qs = TrainingCourse.objects.filter(deadline__isnull=False, mandatory=True)
        if plant:
            tr_qs = tr_qs.filter(plants=plant)
        for tr in tr_qs:
            _add(
                "training_mandatory",
                f"Formazione: {tr.title}",
                tr.deadline,
                tr.status,
                str(tr.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze formazione", exc_info=True)

    # Security committee next meeting
    try:
        from apps.governance.models import SecurityCommittee

        sc_qs = SecurityCommittee.objects.filter(next_meeting_at__isnull=False)
        if plant:
            sc_qs = sc_qs.filter(plant=plant)
        for sc in sc_qs:
            _add(
                "security_committee",
                f"Comitato: {sc.name}",
                sc.next_meeting_at.date(),
                "scheduled",
                str(sc.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze comitato sicurezza", exc_info=True)

    # Audit findings
    try:
        from apps.audit_prep.models import AuditFinding

        af_qs = AuditFinding.objects.filter(
            response_deadline__isnull=False,
            status__in=["open", "in_response"],
        )
        if plant:
            af_qs = af_qs.filter(audit_prep__plant=plant)
        rule_map = {
            "major_nc": "finding_major",
            "minor_nc": "finding_minor",
            "observation": "finding_observation",
            "opportunity": "finding_observation",
        }
        for af in af_qs:
            rule_type = rule_map.get(af.finding_type, "finding_minor")
            _add(
                rule_type,
                f"Finding [{af.finding_type.upper()}]: {af.title}",
                af.response_deadline,
                af.status,
                str(af.id),
            )
    except Exception:
        logger.exception("Errore nel calcolo delle scadenze finding audit", exc_info=True)

    activities.sort(key=lambda x: x["due_date"])
    return activities


# ─── Required documents status ────────────────────────────────────────────────

def resolve_control_instance(req, plant):
    """Risolve la voce di checklist (RequiredDocument.iso_clause) al ControlInstance
    reale del sito, se esiste.

    L'iso_clause è testo libero e non allineato al formato ``external_id``:
      - TISAX: "ISA 6.1.1" ↔ external_id "ISA-6.1.1" (spazio→trattino);
      - ISO Annex A: "A.5.1" ↔ "A.5.1" (match esatto).
    Le clausole gestionali ISO (es. "9.3") non hanno un controllo Annex A: in tal
    caso non si risolve nulla e la voce resta puramente documentale.
    """
    if not plant or not req.iso_clause:
        return None
    from apps.controls.models import ControlInstance

    raw = req.iso_clause.strip()
    candidates = {raw, raw.replace(" ", "-"), raw.replace("ISA ", "ISA-")}
    return (
        ControlInstance.objects.filter(
            plant=plant,
            control__external_id__in=list(candidates),
            deleted_at__isnull=True,
        )
        .select_related("control")
        .first()
    )


def _control_applicability(req, plant):
    """Applicabilità del requisito al plant, derivata dal controllo mappato.

    Ritorna:
      - ("resolvable", ci)          esiste una ControlInstance sul plant → il
        documento è control-backed e collegabile;
      - ("excluded", None)          il controllo esiste ma è "level-gated" (es.
        level='essential') e NON ha istanza sul plant → fuori scope per la
        classificazione NIS2 del sito (essenziale/importante) → il documento
        NON è richiesto e va NASCOSTO;
      - ("control_no_instance", None) il controllo esiste, NON è level-gated, ma
        non ha istanza sul plant (buco di istanziazione, es. framework attivo
        senza controlli generati) → il documento è comunque control-backed e va
        MOSTRATO (rosso), non nascosto;
      - ("no_control", None)        nessun controllo corrispondente (documento di
        sistema, es. clausole gestionali ISO) → mostrato, con euristica per tipo.

    Solo i controlli level-gated senza istanza vengono nascosti: così la checklist
    si adatta alla classificazione del plant senza sopprimere documenti per un
    semplice buco di istanziazione.
    """
    ci = resolve_control_instance(req, plant)
    if ci is not None:
        return "resolvable", ci
    raw = (req.iso_clause or "").strip()
    if not raw:
        return "no_control", None
    from apps.controls.models import Control, Framework

    candidates = {raw, raw.replace(" ", "-"), raw.replace("ISA ", "ISA-")}
    fw = Framework.objects.filter(code=req.framework).first()
    ctrl = (
        Control.objects.filter(
            framework=fw, external_id__in=list(candidates), deleted_at__isnull=True
        ).first()
        if fw
        else None
    )
    if ctrl is None:
        return "no_control", None
    if (ctrl.level or "") != "":
        # Controllo applicabile solo a certe classificazioni (es. 'essential'):
        # se non ha istanza sul plant è fuori scope → nascondi.
        return "excluded", None
    # Controllo standard senza istanza: buco dati, ma resta control-backed.
    return "control_no_instance", None


def _linkables_for_control(ci):
    """Document ed Evidence collegati al controllo (non cancellati)."""
    if ci is None:
        return [], []
    docs = list(ci.documents.filter(deleted_at__isnull=True))
    evs = list(ci.evidences.filter(deleted_at__isnull=True))
    return docs, evs


def _evidence_is_valid(ev):
    import datetime
    if ev.valid_until is None:
        return True
    return ev.valid_until >= datetime.date.today()


def _fulfillment_status(fulfillment):
    """(traffic_light, info dict) per un aggancio esplicito.

    Verde solo se l'elemento agganciato è "valido": Document approvato oppure
    Evidence non scaduta. Altrimenti giallo (agganciato ma non valido).
    """
    doc = fulfillment.document
    ev = fulfillment.evidence
    if doc is not None and doc.deleted_at is None:
        valid = doc.status == "approvato"
        info = {
            "kind": "document",
            "id": str(doc.id),
            "title": doc.title,
            "status": doc.status,
            "valid_until": None,
            "linked_by": fulfillment.linked_by.username if fulfillment.linked_by else None,
            "linked_at": fulfillment.linked_at.isoformat() if fulfillment.linked_at else None,
        }
        return ("green" if valid else "yellow"), info
    if ev is not None and ev.deleted_at is None:
        valid = _evidence_is_valid(ev)
        info = {
            "kind": "evidence",
            "id": str(ev.id),
            "title": ev.title,
            "status": "valida" if valid else "scaduta",
            "valid_until": str(ev.valid_until) if ev.valid_until else None,
            "linked_by": fulfillment.linked_by.username if fulfillment.linked_by else None,
            "linked_at": fulfillment.linked_at.isoformat() if fulfillment.linked_at else None,
        }
        return ("green" if valid else "yellow"), info
    # target cancellato/mancante → aggancio non più valido
    return None, None


def get_required_documents_status(plant=None, framework: str = "ISO27001") -> list[dict]:
    """
    Per ogni RequiredDocument del framework calcola il semaforo.

    Priorità:
      1. Se esiste un aggancio esplicito (RequiredDocumentFulfillment) valido →
         usa quello (verde se valido, giallo se agganciato ma non valido).
      2. Altrimenti fallback all'euristica storica per tipo di documento.
    Espone anche il controllo risolto e il numero di elementi agganciabili, così
    il frontend può offrire il picker "solo elementi collegati al controllo".
    """
    # I documenti obbligatori sono per-sito: senza un plant non c'è scoping
    # affidabile (né classificazione né framework attivo) → nessun risultato.
    if plant is None:
        return []

    # Verifica che il framework sia attivo per questo plant
    from apps.plants.services import get_active_framework_codes
    active_codes = get_active_framework_codes(plant)
    if framework not in active_codes:
        return []

    from django.db.models import Q
    from .models import RequiredDocument, RequiredDocumentFulfillment

    required = RequiredDocument.objects.filter(framework=framework)
    result = []

    # RequiredDocument usa chiavi inglesi (policy/procedure/record),
    # Document.document_type usa chiavi italiane (policy/procedura/registro).
    _TYPE_MAP = {"procedure": "procedura", "record": "registro"}

    # Precarica gli agganci del sito per questo set di requisiti.
    fulfillments = {}
    if plant:
        for f in RequiredDocumentFulfillment.objects.filter(
            plant=plant, required_document__framework=framework, deleted_at__isnull=True
        ).select_related("document", "evidence", "linked_by"):
            fulfillments[str(f.required_document_id)] = f

    for req in required:
        # plant è garantito non-None qui (ritorno anticipato sopra).
        applicability, ci = _control_applicability(req, plant)
        if applicability == "excluded":
            # Controllo level-gated fuori scope per la classificazione del plant
            # (es. controllo 'essential' su entità 'importante'): il documento
            # non è richiesto qui → escluso dalla checklist.
            continue
        control_backed = applicability in ("resolvable", "control_no_instance")
        control_info = None
        linkable_count = 0
        if ci is not None:
            docs, evs = _linkables_for_control(ci)
            linkable_count = len(docs) + len(evs)
            control_info = {
                "instance_id": str(ci.id),
                "external_id": ci.control.external_id,
                "title": ci.control.get_title(),
            }

        traffic = None
        doc_info = None
        fulfillment_info = None

        # 1) Aggancio esplicito
        f = fulfillments.get(str(req.id))
        if f is not None:
            f_traffic, f_info = _fulfillment_status(f)
            if f_traffic is not None:
                traffic = f_traffic
                fulfillment_info = f_info

        # 2) Requisito ANCORATO a un controllo: nessuna euristica per tipo.
        #    Verde solo via aggancio esplicito al controllo (già gestito sopra):
        #    se manca, resta rosso. Evita falsi verdi con documenti generici non
        #    collegati al controllo (es. un manuale ISMS che colora tutte le
        #    procedure). Vale anche per controllo senza istanza (control-backed).
        if traffic is None and control_backed:
            traffic = "red"

        # 3) Requisito NON ancorato a un controllo (es. clausole gestionali ISO
        #    come SoA, riesame, audit): fallback euristico per tipo di documento
        #    come unico segnale disponibile.
        if traffic is None:
            try:
                from apps.documents.models import Document
                doc_type = _TYPE_MAP.get(req.document_type, req.document_type)
                doc_qs = Document.objects.filter(
                    document_type=doc_type,
                    deleted_at__isnull=True,
                )
                if plant:
                    doc_qs = doc_qs.filter(Q(plant=plant) | Q(shared_plants=plant))
                doc = doc_qs.order_by("-updated_at").first()
            except Exception:
                doc = None

            if doc is None:
                traffic = "red"
            elif doc.status == "approvato":
                traffic = "green"
                doc_info = {"id": str(doc.id), "title": doc.title, "status": doc.status, "review_due_date": str(doc.review_due_date) if doc.review_due_date else None}
            else:
                traffic = "yellow"
                doc_info = {"id": str(doc.id), "title": doc.title, "status": doc.status, "review_due_date": str(doc.review_due_date) if doc.review_due_date else None}

        # Stato del controllo per il frontend (messaggistica del picker):
        #   resolved     → controllo attivo sul sito, collegabile
        #   no_instance  → controllo esiste ma non attivo su questo sito
        #   system       → documento di sistema non legato ad alcun controllo
        control_status = {
            "resolvable": "resolved",
            "control_no_instance": "no_instance",
            "no_control": "system",
        }.get(applicability, "system")

        result.append({
            "id": str(req.id),
            "document_type": req.document_type,
            "description": req.description,
            "iso_clause": req.iso_clause,
            "mandatory": req.mandatory,
            "notes": req.notes,
            "traffic_light": traffic,
            "document": doc_info,
            "control": control_info,
            "control_status": control_status,
            "linkable_count": linkable_count,
            "fulfillment": fulfillment_info,
        })

    return result


def get_required_document_linkables(req, plant) -> dict:
    """Elementi selezionabili per soddisfare un requisito: SOLO Document ed
    Evidence già collegati al controllo risolto per quel sito."""
    ci = resolve_control_instance(req, plant)
    if ci is None:
        return {"control": None, "documents": [], "evidences": []}
    docs, evs = _linkables_for_control(ci)
    return {
        "control": {
            "instance_id": str(ci.id),
            "external_id": ci.control.external_id,
            "title": ci.control.get_title(),
        },
        "documents": [
            {"id": str(d.id), "title": d.title, "document_type": d.document_type, "status": d.status}
            for d in docs
        ],
        "evidences": [
            {
                "id": str(e.id),
                "title": e.title,
                "evidence_type": e.evidence_type,
                "valid_until": str(e.valid_until) if e.valid_until else None,
                "valid": _evidence_is_valid(e),
            }
            for e in evs
        ],
    }


def link_required_document(req, plant, user, document=None, evidence=None):
    """Crea/sostituisce l'aggancio del requisito per il sito. Valida che il
    target sia effettivamente collegato al controllo risolto (scope "solo
    collegati al controllo")."""
    from django.core.exceptions import ValidationError
    from .models import RequiredDocumentFulfillment

    if (document is None) == (evidence is None):
        raise ValidationError("Specificare esattamente un document oppure una evidence.")

    ci = resolve_control_instance(req, plant)
    if ci is None:
        raise ValidationError(
            "Nessun controllo risolvibile per questo requisito/sito: impossibile "
            "verificare il collegamento."
        )
    docs, evs = _linkables_for_control(ci)
    if document is not None and document.id not in {d.id for d in docs}:
        raise ValidationError("Il documento selezionato non è collegato al controllo.")
    if evidence is not None and evidence.id not in {e.id for e in evs}:
        raise ValidationError("L'evidenza selezionata non è collegata al controllo.")

    fulfillment, _created = RequiredDocumentFulfillment.objects.update_or_create(
        plant=plant,
        required_document=req,
        defaults={
            "document": document,
            "evidence": evidence,
            "linked_by": user,
            "deleted_at": None,
        },
    )
    return fulfillment


def unlink_required_document(req, plant):
    from .models import RequiredDocumentFulfillment

    RequiredDocumentFulfillment.objects.filter(
        plant=plant, required_document=req
    ).delete()
