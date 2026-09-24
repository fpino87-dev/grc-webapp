import datetime
import hashlib
import html
import logging
import uuid

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from core.audit import log_action

from .framework_hierarchy import expand_tisax
from .models import AuditFinding, AuditGroup, AuditPrep, AuditProgram

DEADLINE_DAYS = {
    "major_nc":    30,
    "minor_nc":    90,
    "observation": 180,
    "opportunity": None,
}

_RULE_TYPE_MAP = {
    "major_nc":    "finding_major",
    "minor_nc":    "finding_minor",
    "observation": "finding_observation",
}

PDCA_TRIGGER_MAP = {
    "major_nc":    "finding_major",
    "minor_nc":    "finding_minor",
    "observation": "finding_observation",
    "opportunity": "finding_opportunity",
}


def calc_readiness_score(audit_prep: AuditPrep) -> int:
    """
    Prontezza 0-100 sulle voci di evidenza.

    Le voci `na` (controllo non applicabile o escluso dalla SoA) restano fuori
    dal calcolo, numeratore e denominatore: contarle come presenti gonfierebbe
    il punteggio, contarle come mancanti lo affosserebbe. Non sono materia di
    prontezza — non c'è niente da preparare.
    """
    items = [i for i in audit_prep.evidence_items.all() if i.status != "na"]
    if not items:
        return 0
    total = len(items)
    score = 0
    for item in items:
        if item.status == "presente":
            score += 1
        elif item.status == "scaduto":
            score += 0.5
    return round(score / total * 100)


def update_readiness_score(audit_prep: AuditPrep) -> AuditPrep:
    """Recalculate and persist the readiness_score field."""
    audit_prep.readiness_score = calc_readiness_score(audit_prep)
    audit_prep.save(update_fields=["readiness_score", "updated_at"])
    return audit_prep


def finalize_new_prep(prep: AuditPrep, user) -> None:
    """Passi comuni a ogni AuditPrep appena creato (singolo o di un gruppo).

    Seeding automatico per i framework TISAX gerarchici (L3/PROTO): gli
    EvidenceItem coprono anche il livello inferiore (L2 estesa da L3, L2+L3
    estesi da PROTO). Per gli altri framework il seed resta opzionale e a
    carico dell'utente, per non alterare il flusso manuale esistente.
    """
    fw_code = prep.framework.code if prep.framework_id else None
    if fw_code in ("TISAX_L3", "TISAX_PROTO"):
        seed_evidence_items_for_prep(
            prep,
            framework_codes=[fw_code],
            coverage_type=prep.coverage_type or "campione",
            user=user,
        )
        log_action(
            user=user,
            action_code="audit_prep.evidence.auto_seeded",
            level="L2",
            entity=prep,
            payload={
                "frameworks_requested": [fw_code],
                "frameworks_expanded": expand_tisax([fw_code]),
                "items_count": prep.evidence_items.count(),
            },
        )
    log_action(
        user=user,
        action_code="audit_prep.auditprep.create",
        level="L2",
        entity=prep,
        payload={"id": str(prep.id), "title": prep.title,
                 "group": str(prep.group_id) if prep.group_id else None},
    )


# ── Audit multi-sito ─────────────────────────────────────────────────────────

# Dati dell'audit comune copiati su ogni AuditPrep del gruppo.
GROUP_SHARED_FIELDS = ("audit_type", "requesting_party", "auditor_name", "audit_date", "framework")


def create_audit_group(*, user, title: str, plants, framework=None, audit_type="interno",
                       requesting_party="", auditor_name="", audit_date=None, scope_id="",
                       coverage_type="campione") -> AuditGroup:
    """Crea un audit comune a più siti: il gruppo con i dati condivisi e un
    AuditPrep per sito (checklist, prontezza e finding restano per sito).
    Il framework, se indicato, deve essere assegnato a tutti i siti."""
    from django.core.exceptions import ValidationError

    plants = list(dict.fromkeys(plants))
    if len(plants) < 2:
        raise ValidationError(_("Un audit multi-sito richiede almeno due siti."))
    if framework is not None:
        from apps.plants.models import PlantFramework

        covered = set(
            PlantFramework.objects.filter(
                plant__in=plants, framework=framework, active=True, deleted_at__isnull=True,
            ).values_list("plant_id", flat=True)
        )
        missing = [p.code for p in plants if p.pk not in covered]
        if missing:
            raise ValidationError(
                _("Il framework non è assegnato ai siti: %(sites)s.") % {"sites": ", ".join(missing)}
            )

    with transaction.atomic():
        group = AuditGroup.objects.create(
            title=title, framework=framework, audit_type=audit_type,
            requesting_party=requesting_party if audit_type == "seconda_parte" else "",
            auditor_name=auditor_name, audit_date=audit_date, scope_id=scope_id,
            created_by=user,
        )
        for plant in plants:
            prep = AuditPrep.objects.create(
                plant=plant, group=group, title=f"{title} — {plant.code}",
                coverage_type=coverage_type, created_by=user,
                **{f: getattr(group, f) for f in GROUP_SHARED_FIELDS},
            )
            finalize_new_prep(prep, user)
        log_action(
            user=user,
            action_code="audit_prep.group.create",
            level="L2",
            entity=group,
            payload={"title": title, "plants": [p.code for p in plants], "audit_type": audit_type},
        )
    return group


def update_audit_group(group: AuditGroup, user, **fields) -> AuditGroup:
    """Aggiorna i dati comuni e li riporta su tutti gli audit dei siti."""
    allowed = {k: v for k, v in fields.items() if k in (*GROUP_SHARED_FIELDS, "title", "scope_id")}
    if allowed.get("audit_type", group.audit_type) != "seconda_parte":
        allowed["requesting_party"] = ""
    with transaction.atomic():
        for k, v in allowed.items():
            setattr(group, k, v)
        group.save()
        shared = {f: getattr(group, f) for f in GROUP_SHARED_FIELDS}
        group.preps.update(**shared, updated_at=timezone.now())
        log_action(
            user=user,
            action_code="audit_prep.group.updated",
            level="L2",
            entity=group,
            payload={"fields": sorted(allowed)},
        )
    return group


def attach_group_report(group: AuditGroup, uploaded_file, user, title: str = ""):
    """Rapporto ufficiale unico per l'audit multi-sito, collegato a tutti gli
    audit dei siti. L'evidenza sta sul primo sito del gruppo; gli altri siti
    lo scaricano dal proprio audit (azione report-file)."""
    from apps.documents.services import create_evidence_with_file

    first = group.preps.select_related("plant").order_by("plant__code").first()
    previous_id = group.report_evidence_id
    data = {
        "title": (title.strip() or _("Rapporto audit — %(title)s") % {"title": group.title})[:300],
        "evidence_type": "report",
        "description": _("Rapporto ufficiale dell'audit «%(title)s».") % {"title": group.title},
        "plant": str(first.plant_id) if first else "",
    }
    with transaction.atomic():
        evidence = create_evidence_with_file(data, uploaded_file, user)
        group.report_evidence = evidence
        group.save(update_fields=["report_evidence", "updated_at"])
        group.preps.update(report_evidence=evidence, updated_at=timezone.now())
        log_action(
            user=user,
            action_code="audit_prep.official_report.attached",
            level="L2",
            entity=group,
            payload={
                "evidence_id": str(evidence.pk),
                "replaced_evidence_id": str(previous_id) if previous_id else None,
                "audit_type": group.audit_type,
                "preps": [str(pk) for pk in group.preps.values_list("pk", flat=True)],
            },
        )
    return evidence


def detach_group_report(group: AuditGroup, user) -> None:
    previous_id = group.report_evidence_id
    if not previous_id:
        return
    with transaction.atomic():
        group.report_evidence = None
        group.save(update_fields=["report_evidence", "updated_at"])
        group.preps.update(report_evidence=None, updated_at=timezone.now())
        log_action(
            user=user,
            action_code="audit_prep.official_report.detached",
            level="L2",
            entity=group,
            payload={"evidence_id": str(previous_id)},
        )


def open_group_finding(audit_prep: AuditPrep, **kwargs) -> list[AuditFinding]:
    """Rilievo comune a tutti i siti di un audit multi-sito: un finding per
    sito (con PDCA, scadenza e task sul sito), legati dallo stesso common_key.
    Il primo della lista è quello dell'audit da cui è stato registrato."""
    if not audit_prep.group_id:
        return [open_finding(audit_prep, **kwargs)]
    key = uuid.uuid4()
    preps = [audit_prep] + list(
        audit_prep.group.preps.exclude(pk=audit_prep.pk).select_related("plant").order_by("plant__code")
    )
    with transaction.atomic():
        return [open_finding(p, common_key=key, **kwargs) for p in preps]


def open_finding(audit_prep, finding_type: str, title: str,
                 description: str, audit_date, user,
                 control_instance=None,
                 auditor_name: str = "",
                 auto_generated: bool = False,
                 common_key=None) -> AuditFinding:
    """
    Crea un AuditFinding e genera automaticamente:
    - PDCA (obbligatorio per major/minor)
    - Scadenza risposta calcolata
    - Task se major NC
    """
    from apps.pdca.services import create_cycle

    deadline = None
    rule_type = _RULE_TYPE_MAP.get(finding_type)
    if rule_type:
        try:
            from apps.compliance_schedule.services import get_due_date
            base_date = audit_date if hasattr(audit_date, "year") else timezone.localdate()
            deadline = get_due_date(rule_type, plant=audit_prep.plant, from_date=base_date)
        except Exception:
            deadline_days = DEADLINE_DAYS.get(finding_type)
            if deadline_days:
                base_date = audit_date if hasattr(audit_date, "year") else timezone.localdate()
                deadline = base_date + datetime.timedelta(days=deadline_days)

    finding = AuditFinding.objects.create(
        audit_prep=audit_prep,
        control_instance=control_instance,
        finding_type=finding_type,
        title=title,
        description=description,
        # In mancanza di un nome sul finding vale l'auditor/ente dell'audit.
        auditor_name=auditor_name or audit_prep.auditor_name,
        audit_date=audit_date,
        response_deadline=deadline,
        status="open",
        auto_generated=auto_generated,
        common_key=common_key,
        created_by=user,
    )

    # Crea PDCA automatico per major e minor NC
    if finding_type in ("major_nc", "minor_nc"):
        cycle_title = f"[{finding_type.upper()}] {title}"
        cycle = create_cycle(
            plant=audit_prep.plant,
            title=cycle_title,
            trigger_type=PDCA_TRIGGER_MAP[finding_type],
            trigger_source_id=finding.pk,
            scope_type="finding",
            scope_id=finding.pk,
        )
        # Il PDCA eredita il tipo di audit (interno / seconda / terza parte).
        cycle.audit_subtype = audit_prep.audit_type
        cycle.save(update_fields=["audit_subtype", "updated_at"])
        finding.pdca_cycle = cycle
        finding.save(update_fields=["pdca_cycle"])

    # Task urgente per major NC
    if finding_type == "major_nc":
        from apps.tasks.services import create_task
        create_task(
            plant=audit_prep.plant,
            title=f"MAJOR NC: {title}",
            description=(
                f"Non conformita' maggiore rilevata in audit.\n"
                f"Scadenza risposta: {deadline}\n\n{description}"
            ),
            priority="critica",
            source_module="M17",
            source_id=finding.pk,
            due_date=deadline,
            assign_type="role",
            assign_value="compliance_officer",
        )

    # Notifiche configurabili per finding
    try:
        from apps.notifications.resolver import fire_notification

        event = "finding_major" if finding_type == "major_nc" else "finding_minor"
        fire_notification(
            event,
            plant=audit_prep.plant,
            context={"finding": finding},
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("audit_prep: notifica finding non inviata: %s", exc)

    log_action(
        user=user,
        action_code="audit.finding.opened",
        level="L1" if finding_type == "major_nc" else "L2",
        entity=finding,
        payload={
            "finding_type": finding_type,
            "title": title[:100],
            "deadline": str(deadline) if deadline else None,
            "has_pdca": finding.pdca_cycle is not None,
        },
    )
    return finding


# ── Collegamento finding ↔ PDCA ──────────────────────────────────────────────

FINDING_LABEL = {
    "major_nc": "MAJOR_NC", "minor_nc": "MINOR_NC",
    "observation": "OBSERVATION", "opportunity": "OPPORTUNITY",
}


def _check_linkable(finding: AuditFinding, cycle) -> None:
    """Regole del collegamento (opzione A): un finding ha al massimo un PDCA;
    un PDCA può coprire più finding, ma dello stesso audit e sito."""
    from django.core.exceptions import ValidationError

    if finding.pdca_cycle_id:
        raise ValidationError(_("Il finding è già collegato a un PDCA."))
    if finding.status in ("closed", "accepted_by_auditor"):
        raise ValidationError(_("Il finding è chiuso: non si collega a un PDCA."))
    if cycle.fase_corrente in ("chiuso", "archiviato"):
        raise ValidationError(_("Il PDCA è chiuso o archiviato."))
    if cycle.plant_id != finding.audit_prep.plant_id:
        raise ValidationError(_("Il PDCA deve essere dello stesso sito dell'audit."))
    other = cycle.findings.exclude(audit_prep_id=finding.audit_prep_id).first()
    if other:
        raise ValidationError(_(
            "Il PDCA copre già finding di un altro audit («%(audit)s»): si possono "
            "collegare solo finding dello stesso audit."
        ) % {"audit": other.audit_prep.title})


def link_finding_to_pdca(finding: AuditFinding, cycle, user) -> AuditFinding:
    """Collega un finding a un PDCA esistente (dal finding o dal menù PDCA)."""
    with transaction.atomic():
        _check_linkable(finding, cycle)
        finding.pdca_cycle = cycle
        finding.save(update_fields=["pdca_cycle", "updated_at"])
        if not cycle.audit_subtype:
            cycle.audit_subtype = finding.audit_prep.audit_type
            cycle.save(update_fields=["audit_subtype", "updated_at"])
        log_action(
            user=user,
            action_code="audit.finding.pdca_linked",
            level="L2",
            entity=finding,
            payload={"pdca_cycle": str(cycle.pk), "audit_prep": str(finding.audit_prep_id)},
        )
    return finding


def open_pdca_for_finding(finding: AuditFinding, user, title: str = "", descrizione: str = ""):
    """Apre un PDCA già collegato al finding: sito dell'audit, trigger dal tipo
    di finding e tipo di audit (interno / seconda / terza parte)."""
    from django.core.exceptions import ValidationError
    from apps.pdca.services import create_cycle

    if finding.pdca_cycle_id:
        raise ValidationError(_("Il finding è già collegato a un PDCA."))
    prep = finding.audit_prep
    with transaction.atomic():
        cycle = create_cycle(
            plant=prep.plant,
            title=(title.strip() or f"[{FINDING_LABEL[finding.finding_type]}] {finding.title}")[:255],
            trigger_type=PDCA_TRIGGER_MAP[finding.finding_type],
            trigger_source_id=finding.pk,
            scope_type="finding",
            scope_id=finding.pk,
        )
        cycle.audit_subtype = prep.audit_type
        cycle.descrizione = descrizione or finding.description
        cycle.created_by = user
        cycle.save(update_fields=["audit_subtype", "descrizione", "created_by", "updated_at"])
        log_action(
            user=user, action_code="pdca.cycle.create", level="L2", entity=cycle,
            payload={"cycle_id": str(cycle.pk), "title": cycle.title, "finding": str(finding.pk)},
        )
        link_finding_to_pdca(finding, cycle, user)
    return cycle


def unlink_finding_from_pdca(finding: AuditFinding, user, reason: str) -> AuditFinding:
    """Scollega un PDCA collegato per errore: motivazione obbligatoria, resta
    nell'audit trail. Il PDCA non viene toccato."""
    from django.core.exceptions import ValidationError

    if not finding.pdca_cycle_id:
        raise ValidationError(_("Il finding non è collegato a un PDCA."))
    if finding.status in ("closed", "accepted_by_auditor"):
        raise ValidationError(_("Il finding è chiuso: il collegamento non si modifica più."))
    if not reason or len(reason.strip()) < 10:
        raise ValidationError(_("Motivo obbligatorio (minimo 10 caratteri)."))
    previous = finding.pdca_cycle_id
    with transaction.atomic():
        finding.pdca_cycle = None
        finding.save(update_fields=["pdca_cycle", "updated_at"])
        log_action(
            user=user,
            action_code="audit.finding.pdca_unlinked",
            level="L2",
            entity=finding,
            payload={"pdca_cycle": str(previous), "reason": reason.strip()[:200]},
        )
    return finding


@transaction.atomic
def close_finding(finding: AuditFinding, user,
                  closure_notes: str = "",
                  evidence=None) -> AuditFinding:
    """
    Chiude un AuditFinding.
    Richiede evidenza per major e minor NC.
    Crea automaticamente Lesson Learned.
    Aggiorna ControlInstance se collegato.

    Con un PDCA collegato il finding si chiude solo a azione correttiva
    completata: ciclo già chiuso/archiviato, oppure in ACT e senza altri
    finding aperti collegati (in tal caso il ciclo si chiude qui, con le note
    di chiusura come standardizzazione). Tutte le verifiche precedono le
    scritture e la funzione è atomica: nessuno stato a metà.
    """
    from django.core.exceptions import ValidationError

    if finding.finding_type in ("major_nc", "minor_nc"):
        if evidence is None:
            raise ValidationError(
                _("Per chiudere una non conformità è obbligatoria un'evidenza di chiusura.")
            )
        if not closure_notes or len(closure_notes.strip()) < 20:
            raise ValidationError(
                _("Le note di chiusura devono essere almeno 20 caratteri.")
            )

    cycle = finding.pdca_cycle
    close_cycle_too = False
    if cycle and cycle.fase_corrente not in ("chiuso", "archiviato"):
        others_open = cycle.findings.exclude(pk=finding.pk).exclude(
            status__in=["closed", "accepted_by_auditor"]
        ).exists()
        if cycle.fase_corrente != "act" or others_open:
            raise ValidationError(_(
                "Il PDCA collegato «%(title)s» è in fase %(phase)s: il finding si chiude "
                "quando l'azione correttiva è completata (PDCA in ACT o chiuso)."
            ) % {"title": cycle.title, "phase": cycle.fase_corrente.upper()})
        if not closure_notes or len(closure_notes.strip()) < 20:
            raise ValidationError(_(
                "Il PDCA collegato è in ACT e verrà chiuso insieme al finding: descrivi "
                "nelle note di chiusura l'azione standardizzata (minimo 20 caratteri)."
            ))
        close_cycle_too = True

    finding.status = "closed"
    finding.closure_notes = closure_notes
    finding.closure_evidence = evidence
    finding.closed_at = timezone.now()
    finding.closed_by = user
    finding.save(update_fields=[
        "status", "closure_notes", "closure_evidence",
        "closed_at", "closed_by", "updated_at",
    ])

    # Aggiorna ControlInstance se collegato
    if finding.control_instance:
        ci = finding.control_instance
        if ci.status == "gap":
            ci.status = "parziale"
            ci.save(update_fields=["status", "updated_at"])

    # PDCA in ACT con solo questo finding aperto: si chiude con lui.
    if close_cycle_too:
        from apps.pdca.services import close_cycle
        close_cycle(cycle, user, act_description=closure_notes)

    # Crea Lesson Learned automatica
    from apps.lessons.models import LessonLearned
    ll = LessonLearned.objects.create(
        plant=finding.audit_prep.plant,
        title=f"[Finding] {finding.title}",
        description=(
            f"Tipo: {finding.finding_type}\n"
            f"Auditor: {finding.auditor_name}\n"
            f"Causa radice: {finding.root_cause}\n"
            f"Azione correttiva: {finding.corrective_action}\n"
            f"Note chiusura: {closure_notes}"
        ),
        category="audit",
        source_module="M17",
        source_id=finding.pk,
        created_by=user,
    )
    finding.lesson_learned = ll
    finding.save(update_fields=["lesson_learned"])

    log_action(
        user=user,
        action_code="audit.finding.closed",
        level="L1" if finding.finding_type == "major_nc" else "L2",
        entity=finding,
        payload={
            "finding_type": finding.finding_type,
            "has_evidence": evidence is not None,
            "lesson_id": str(ll.pk),
        },
    )
    return finding


def suggest_audit_plan(plant, frameworks, year: int,
                       coverage_type: str = "campione") -> list:
    """
    Suggerisce un piano audit annuale basato sui gap aperti.
    Distribuisce i domini nei 4 trimestri in modo bilanciato,
    prioritizzando i domini con più controlli in GAP o PARZIALE.
    """
    from apps.controls.models import ControlDomain
    from django.db.models import Count, Q

    domain_scores = []
    for fw in frameworks:
        domains = ControlDomain.objects.filter(
            framework=fw,
            deleted_at__isnull=True,
        ).annotate(
            gap_count=Count(
                "controls__instances",
                filter=Q(
                    controls__instances__plant=plant,
                    controls__instances__status__in=["gap", "parziale"],
                    controls__instances__deleted_at__isnull=True,
                )
            ),
            total_count=Count(
                "controls__instances",
                filter=Q(
                    controls__instances__plant=plant,
                    controls__instances__deleted_at__isnull=True,
                )
            ),
        ).order_by("-gap_count")

        for domain in domains:
            if domain.total_count == 0:
                continue
            gap_pct = domain.gap_count / domain.total_count * 100
            domain_scores.append({
                "domain_id":    str(domain.pk),
                "domain_code":  domain.code or domain.external_id or str(domain.pk),
                "domain_name":  domain.get_name("it"),
                "framework":    fw.code,
                "gap_count":    domain.gap_count,
                "total_count":  domain.total_count,
                "gap_pct":      round(gap_pct, 1),
                "priority":     ("alta" if gap_pct >= 50
                                 else "media" if gap_pct >= 20
                                 else "bassa"),
            })

    # Deduplicazione domini presenti in più framework:
    # mantieni il record con gap_pct più alto e concatena i framework
    seen_domains: dict = {}
    for ds in domain_scores:
        key = ds["domain_code"]
        if key not in seen_domains or ds["gap_pct"] > seen_domains[key]["gap_pct"]:
            if key in seen_domains:
                existing_fw = seen_domains[key].get("framework", "")
                ds["framework"] = f"{existing_fw}+{ds['framework']}"
            seen_domains[key] = ds
    domain_scores = list(seen_domains.values())
    domain_scores.sort(key=lambda x: x["gap_pct"], reverse=True)

    total_domains = len(domain_scores)
    coverage_pct = {"campione": 0.25, "esteso": 0.50, "full": 1.0}.get(coverage_type, 0.25)
    domains_per_year = max(4, int(total_domains * coverage_pct))
    domains_per_q = max(1, domains_per_year // 4)

    quarter_months = {1: "03", 2: "06", 3: "09", 4: "12"}
    planned = []

    for q in range(1, 5):
        start_idx = (q - 1) * domains_per_q
        end_idx = start_idx + domains_per_q
        q_domains = domain_scores[start_idx:end_idx]

        if q in (1, 3) and domain_scores:
            high_priority = [d for d in domain_scores
                             if d["priority"] == "alta" and d not in q_domains]
            q_domains = (high_priority[:2] + q_domains)[:domains_per_q + 2]

        fw_codes = list({d["framework"] for d in q_domains}) or [fw.code for fw in frameworks]

        planned.append({
            "id":                str(uuid.uuid4()),
            "quarter":           q,
            "title":             f"Audit Q{q} {year} — {' + '.join(fw_codes)}",
            "framework_codes":   fw_codes,
            "coverage_type":     coverage_type,
            "scope_domains":     [d["domain_code"] for d in q_domains],
            "suggested_domains": [d["domain_code"] for d in q_domains],
            "domain_details":    q_domains,
            "auditor_type":      "interno",
            "auditor_name":      "",
            "auditor_token":     None,
            "planned_date":      f"{year}-{quarter_months[q]}-15",
            "actual_date":       None,
            "audit_prep_id":     None,
            "status":            "planned",
            "notes":             "",
        })

    return planned


def seed_evidence_items_for_prep(
    prep: "AuditPrep",
    framework_codes: list[str],
    *,
    scope_domains: list[str] | None = None,
    coverage_type: str = "campione",
    user=None,
    seed_key: str | None = None,
    only_missing: bool = False,
) -> int:
    """
    Genera (o integra) gli `EvidenceItem` di un `AuditPrep` a partire dai
    `ControlInstance` del plant, applicando l'espansione gerarchica TISAX.

    - `framework_codes`: codici richiesti dall'utente (es. ["TISAX_L3"]). La
      gerarchia TISAX viene applicata via `expand_tisax`.
    - `scope_domains`: opzionale, restringe ai domini specificati (per code
      o external_id).
    - `coverage_type`: "campione" (~25%), "esteso" (~50%), "full" (100%).
    - `seed_key`: chiave per il random deterministico (stessa scelta a parità
      di chiave). Default: pk del prep.
    - `only_missing`: se True, non crea EvidenceItem per ControlInstance gia'
      presenti nel prep — usato dal sync per allineare prep esistenti.

    Restituisce il numero di EvidenceItem creati.
    """
    import random as _rnd
    from django.db.models import Q
    from apps.controls.models import ControlInstance, Framework
    from .models import EvidenceItem

    expanded_codes = expand_tisax(framework_codes)
    frameworks = list(Framework.objects.filter(code__in=expanded_codes))
    if not frameworks:
        return 0

    seed_str = seed_key or str(prep.pk)
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2 ** 31)
    rng = _rnd.Random(seed)

    existing_ci_ids: set = set()
    if only_missing:
        existing_ci_ids = set(
            prep.evidence_items
            .filter(deleted_at__isnull=True, control_instance__isnull=False)
            .values_list("control_instance_id", flat=True)
        )

    items_to_create = []
    for fw in frameworks:
        instances = ControlInstance.objects.filter(
            plant=prep.plant,
            control__framework=fw,
            deleted_at__isnull=True,
        ).select_related("control__domain")

        if scope_domains:
            instances = instances.filter(
                Q(control__domain__code__in=scope_domains) |
                Q(control__domain__external_id__in=scope_domains)
            )

        instance_list = list(instances)

        # I controlli non applicabili non sono materia di verifica: restano in
        # elenco (in audit le esclusioni si verificano) ma non entrano nel
        # campione, altrimenti consumerebbero slot sottraendoli ai controlli
        # che vanno davvero testati.
        not_applicable = [
            i for i in instance_list
            if i.status == "na" or i.applicability != "applicabile"
        ]
        instance_list = [i for i in instance_list if i not in not_applicable]

        if coverage_type == "campione" and len(instance_list) > 10:
            gaps = [i for i in instance_list if i.status in ("gap", "parziale")]
            others = [i for i in instance_list if i.status not in ("gap", "parziale")]
            rng.shuffle(others)
            target = max(5, len(instance_list) // 4)
            instance_list = gaps[:target] + others[:max(0, target - len(gaps))]
        elif coverage_type == "esteso" and len(instance_list) > 10:
            gaps = [i for i in instance_list if i.status in ("gap", "parziale")]
            others = [i for i in instance_list if i.status not in ("gap", "parziale")]
            rng.shuffle(others)
            target = max(5, len(instance_list) // 2)
            instance_list = gaps[:target] + others[:max(0, target - len(gaps))]

        for inst in instance_list + not_applicable:
            if only_missing and inst.pk in existing_ci_ids:
                continue
            items_to_create.append(EvidenceItem(
                audit_prep=prep,
                control_instance=inst,
                description=(
                    f"{inst.control.external_id} — "
                    f"{inst.control.get_title('it')}"
                ),
                status="na" if inst in not_applicable else "mancante",
                created_by=user,
            ))

    EvidenceItem.objects.bulk_create(items_to_create, ignore_conflicts=True)
    return len(items_to_create)


def launch_audit_from_program(program, audit_entry: dict, user) -> "AuditPrep":
    """
    Crea un AuditPrep collegato a un audit pianificato nel programma annuale.
    Precompila gli EvidenceItem applicando l'espansione gerarchica TISAX
    (L3 -> L2+L3, PROTO -> L2+L3+PROTO) e il coverage_type richiesto.
    Atomico: se un qualsiasi passo fallisce nessun record viene persistito.
    """
    from django.db import transaction
    from apps.controls.models import Framework

    with transaction.atomic():
        fw_codes = audit_entry.get("framework_codes", [])
        # Primary framework = primo dei richiesti originali (non espansi):
        # mantiene il "livello" scelto dall'utente nel titolo del prep.
        primary_fw = None
        for code in fw_codes:
            primary_fw = Framework.objects.filter(code=code).first()
            if primary_fw:
                break

        coverage_type = audit_entry.get("coverage_type", "campione")
        prep = AuditPrep.objects.create(
            plant=program.plant,
            framework=primary_fw,
            title=audit_entry["title"],
            audit_date=audit_entry.get("planned_date") or None,
            auditor_name=audit_entry.get("auditor_name", ""),
            status="in_corso",
            audit_program=program,
            audit_entry_id=audit_entry["id"],
            coverage_type=coverage_type,
            created_by=user,
        )

        items_count = seed_evidence_items_for_prep(
            prep,
            framework_codes=fw_codes,
            scope_domains=audit_entry.get("scope_domains", []),
            coverage_type=coverage_type,
            user=user,
            seed_key=f"{program.pk}-{audit_entry.get('quarter', 1)}",
        )

        # Aggiorna audit_prep_id nel JSON del programma
        audits = list(program.planned_audits)
        for a in audits:
            if a.get("id") == audit_entry["id"]:
                a["audit_prep_id"] = str(prep.pk)
                a["status"] = "in_progress"
                a["actual_date"] = str(prep.audit_date or "")
                break
        program.planned_audits = audits
        program.save(update_fields=["planned_audits", "updated_at"])

        # Il promemoria «avvia il prep» ha esaurito il suo scopo nel momento in
        # cui il prep esiste.
        close_program_audit_reminders(program, audit_entry, user)

        log_action(
            user=user,
            action_code="audit_prep.launched_from_program",
            level="L2",
            entity=prep,
            payload={
                "program_id": str(program.pk),
                "quarter": audit_entry["quarter"],
                "coverage": coverage_type,
                "controls_count": items_count,
                "frameworks_requested": list(fw_codes),
                "frameworks_expanded": expand_tisax(fw_codes),
            },
        )
    return prep


def attach_official_report(prep: AuditPrep, uploaded_file, user, title: str = ""):
    """Allega il rapporto ufficiale emesso dall'auditor o dall'ente (es. il
    PDF dell'audit di seconda parte del cliente). Il file diventa un'evidenza
    di tipo "report" sul sito dell'audit, senza scadenza; un rapporto già
    allegato resta tra le evidenze ma non è più quello dell'audit.
    Validazione del file (estensione + MIME) in `create_evidence_with_file`."""
    from apps.documents.services import create_evidence_with_file

    previous_id = prep.report_evidence_id
    data = {
        "title": (title.strip() or _("Rapporto audit — %(title)s") % {"title": prep.title})[:300],
        "evidence_type": "report",
        "description": _("Rapporto ufficiale dell'audit «%(title)s».") % {"title": prep.title},
        "plant": str(prep.plant_id) if prep.plant_id else "",
    }
    with transaction.atomic():
        evidence = create_evidence_with_file(data, uploaded_file, user)
        prep.report_evidence = evidence
        prep.save(update_fields=["report_evidence", "updated_at"])
        log_action(
            user=user,
            action_code="audit_prep.official_report.attached",
            level="L2",
            entity=prep,
            payload={
                "evidence_id": str(evidence.pk),
                "replaced_evidence_id": str(previous_id) if previous_id else None,
                "audit_type": prep.audit_type,
            },
        )
    return evidence


def detach_official_report(prep: AuditPrep, user) -> None:
    """Scollega il rapporto dall'audit; l'evidenza resta archiviata."""
    previous_id = prep.report_evidence_id
    if not previous_id:
        return
    prep.report_evidence = None
    prep.save(update_fields=["report_evidence", "updated_at"])
    log_action(
        user=user,
        action_code="audit_prep.official_report.detached",
        level="L2",
        entity=prep,
        payload={"evidence_id": str(previous_id)},
    )


def generate_audit_report(prep: "AuditPrep") -> str:
    """Genera relazione HTML scaricabile dell'audit."""
    plant_name = prep.plant.name if prep.plant else "—"
    fw_name = prep.framework.name if prep.framework else "—"
    auditor = prep.auditor_name or "—"
    audit_date = prep.audit_date.strftime("%d/%m/%Y") if prep.audit_date else "—"
    audit_type_label = html.escape(prep.get_audit_type_display())
    requesting_party = html.escape(prep.requesting_party or "—")
    score = prep.readiness_score or 0
    score_color = "#16a34a" if score >= 80 else "#d97706" if score >= 60 else "#dc2626"

    items = prep.evidence_items.select_related("control_instance__control__domain").all()
    total = items.count()
    present = items.filter(status="presente").count()
    missing = items.filter(status="mancante").count()
    expired_ev = items.filter(status="scaduto").count()

    items_rows = ""
    for item in items:
        ci = item.control_instance
        ext_id = ci.control.external_id if ci else "—"
        domain = (ci.control.domain.get_name("it") if ci and ci.control.domain else "—")
        ci_status = ci.status if ci else "—"
        status_map = {
            "presente": ("✅", "#16a34a"),
            "mancante": ("❌", "#dc2626"),
            "scaduto":  ("⚠️", "#d97706"),
        }
        icon, color = status_map.get(item.status, ("—", "#6b7280"))
        items_rows += (
            f"<tr><td style='font-family:monospace;font-size:11px'>{ext_id}</td>"
            f"<td>{domain}</td>"
            f"<td style='font-size:11px'>{item.description[:60]}</td>"
            f"<td style='color:{color};font-weight:bold'>{icon} {item.status.title()}</td>"
            f"<td style='color:#4b5563;font-size:11px'>{ci_status}</td>"
            f"<td style='font-size:10px;color:#6b7280'>{item.notes[:50] if item.notes else '—'}</td>"
            f"</tr>"
        )

    findings = list(
        prep.findings.select_related("control_instance__control").all()
    )

    # Contatori pre-calcolati in memoria — nessuna query aggiuntiva
    major_count = sum(1 for f in findings if f.finding_type == "major_nc")
    minor_count = sum(1 for f in findings if f.finding_type == "minor_nc")
    obs_count   = sum(1 for f in findings if f.finding_type == "observation")
    opp_count   = sum(1 for f in findings if f.finding_type == "opportunity")

    type_colors = {
        "major_nc": "#dc2626", "minor_nc": "#d97706",
        "observation": "#2563eb", "opportunity": "#6b7280",
    }
    finding_rows = ""
    for f in findings:
        color = type_colors.get(f.finding_type, "#6b7280")
        finding_rows += (
            f"<tr><td style='color:{color};font-weight:bold'>{f.finding_type.upper()}</td>"
            f"<td>{f.title}</td>"
            f"<td style='font-size:11px'>{f.description[:80]}</td>"
            f"<td style='font-size:11px'>{f.response_deadline or '—'}</td>"
            f"<td><span style='color:{'#dc2626' if f.is_overdue else '#16a34a'}'>{f.status}</span></td>"
            f"</tr>"
        )
    coverage_label = dict(AuditPrep.COVERAGE_CHOICES).get(prep.coverage_type, "—")

    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>Relazione Audit — {prep.title}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:10px;color:#1f2937;margin:24px}}
h1{{font-size:16px;color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:6px}}
h2{{font-size:12px;color:#1e40af;margin-top:18px;border-left:3px solid #1e40af;padding-left:6px}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th{{background:#1e40af;color:white;padding:5px 6px;text-align:left;font-size:9px}}
td{{padding:4px 6px;border-bottom:1px solid #e5e7eb;vertical-align:top}}
tr:nth-child(even){{background:#f9fafb}}
.meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:12px 0}}
.meta-item{{background:#f0f4ff;padding:8px;border-radius:4px}}
.meta-label{{color:#6b7280;font-size:8px}}
.meta-value{{font-weight:bold;font-size:11px}}
.score-box{{text-align:center;padding:16px;border-radius:8px;border:2px solid {score_color};display:inline-block;margin:8px 0}}
.score-num{{font-size:36px;font-weight:bold;color:{score_color}}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0}}
.kpi{{text-align:center;padding:8px;border-radius:4px;background:#f3f4f6}}
.kpi-num{{font-size:20px;font-weight:bold}}
.signature{{border:1px solid #d1d5db;padding:12px;margin-top:24px;border-radius:4px}}
</style></head><body>
<h1>Relazione Audit — {prep.title}</h1>
<div class="meta">
  <div class="meta-item"><div class="meta-label">Sito</div><div class="meta-value">{plant_name}</div></div>
  <div class="meta-item"><div class="meta-label">Framework</div><div class="meta-value">{fw_name}</div></div>
  <div class="meta-item"><div class="meta-label">Data audit</div><div class="meta-value">{audit_date}</div></div>
  <div class="meta-item"><div class="meta-label">Auditor</div><div class="meta-value">{auditor}</div></div>
  <div class="meta-item"><div class="meta-label">Tipo audit</div><div class="meta-value">{audit_type_label}</div></div>
  <div class="meta-item"><div class="meta-label">Committente</div><div class="meta-value">{requesting_party}</div></div>
  <div class="meta-item"><div class="meta-label">Tipo copertura</div><div class="meta-value">{coverage_label}</div></div>
  <div class="meta-item"><div class="meta-label">Generata il</div><div class="meta-value">{timezone.now().strftime("%d/%m/%Y %H:%M")}</div></div>
</div>
<h2>Readiness Score</h2>
<div class="score-box"><div class="score-num">{score}</div><div style="color:{score_color};font-size:10px">/ 100</div></div>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-num">{total}</div><div style="font-size:8px;color:#6b7280">Controlli verificati</div></div>
  <div class="kpi" style="background:#dcfce7"><div class="kpi-num" style="color:#16a34a">{present}</div><div style="font-size:8px;color:#6b7280">Evidenze presenti</div></div>
  <div class="kpi" style="background:#fee2e2"><div class="kpi-num" style="color:#dc2626">{missing}</div><div style="font-size:8px;color:#6b7280">Evidenze mancanti</div></div>
  <div class="kpi" style="background:#fef9c3"><div class="kpi-num" style="color:#d97706">{expired_ev}</div><div style="font-size:8px;color:#6b7280">Evidenze scadute</div></div>
</div>
<h2>Riepilogo Finding</h2>
<div class="kpi-grid">
  <div class="kpi" style="background:#fee2e2"><div class="kpi-num" style="color:#dc2626">{major_count}</div><div style="font-size:8px">Major NC</div></div>
  <div class="kpi" style="background:#fef9c3"><div class="kpi-num" style="color:#d97706">{minor_count}</div><div style="font-size:8px">Minor NC</div></div>
  <div class="kpi" style="background:#dbeafe"><div class="kpi-num" style="color:#2563eb">{obs_count}</div><div style="font-size:8px">Observation</div></div>
  <div class="kpi"><div class="kpi-num">{opp_count}</div><div style="font-size:8px">Opportunity</div></div>
</div>
<h2>Controlli verificati</h2>
<table><tr><th>ID</th><th>Dominio</th><th>Controllo</th><th>Evidenza</th><th>Stato GRC</th><th>Note</th></tr>
{items_rows or "<tr><td colspan='6'>Nessun controllo</td></tr>"}
</table>
<h2>Finding rilevati</h2>
<table><tr><th>Tipo</th><th>Titolo</th><th>Descrizione</th><th>Scadenza</th><th>Stato</th></tr>
{finding_rows or "<tr><td colspan='5'>Nessun finding rilevato</td></tr>"}
</table>
<div class="signature">
  <strong>Firma Auditor</strong><br><br>
  Nome: {auditor} &nbsp;&nbsp; Data: {audit_date}<br><br>
  Firma: _________________________<br><br>
  <strong>Firma CISO / Compliance Officer</strong><br><br>
  Nome: _________________________ &nbsp;&nbsp; Data: _________________________<br><br>
  Firma: _________________________
</div>
</body></html>"""


def close_prep_reminders(prep, user, reason: str = "") -> int:
    """
    Chiude i promemoria aperti su questo prep. Restituisce quanti ne ha chiusi.

    I reminder li genera il giro settimanale (`check_stale_audit_preps`,
    `check_upcoming_audits`) e nessuno li chiudeva: completare o annullare un
    prep lasciava i suoi promemoria aperti a vita, e ogni lunedì se ne
    aggiungeva un altro. Qui si chiudono quando il loro motivo viene meno.
    """
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    open_tasks = Task.objects.filter(
        source_module="M17",
        source_id=prep.pk,
        status__in=["aperto", "in_corso"],
        deleted_at__isnull=True,
    )
    closed = 0
    for task in open_tasks:
        complete_task(task, user, notes=reason or f"Audit prep «{prep.title}» concluso.")
        closed += 1

    # I promemoria nati dal programma annuale («Preparazione audit Q3»,
    # «Avvia AuditPrep Q3») sono agganciati al PROGRAMMA, non al prep: quando
    # nascono il prep ancora non esiste. Vanno chiusi anche da qui, altrimenti
    # sopravvivono alla chiusura dell'audit che li aveva motivati.
    closed += _close_reminders_of_program_entry(prep, user, reason)
    return closed


def _close_reminders_of_program_entry(prep, user, reason: str = "") -> int:
    """Chiude i promemoria di programma dell'audit a cui questo prep si
    riferisce. Nessuno se il prep non nasce da un programma annuale."""
    if not prep.audit_program_id:
        return 0
    program = prep.audit_program
    entry = next(
        (
            a for a in (program.planned_audits or [])
            if a.get("audit_prep_id") == str(prep.pk)
        ),
        None,
    )
    if entry is None:
        return 0
    return close_program_audit_reminders(program, entry, user, reason=reason)


def close_program_audit_reminders(program, audit_entry: dict, user, reason: str = "") -> int:
    """
    Chiude i promemoria «avvia il prep» di un audit pianificato, quando il prep
    è stato effettivamente avviato.

    I reminder di programma sono agganciati al programma, non al singolo audit
    (il prep ancora non esiste quando nascono), quindi il trimestre nel titolo
    è l'unico discriminante — stessa convenzione già usata da `_task_exists`.
    """
    from apps.tasks.models import Task
    from apps.tasks.services import complete_task

    quarter = audit_entry.get("quarter")
    if not quarter:
        return 0

    open_tasks = Task.objects.filter(
        source_module="M17",
        source_id=program.pk,
        status__in=["aperto", "in_corso"],
        deleted_at__isnull=True,
        title__contains=f"Q{quarter}",
    )
    closed = 0
    for task in open_tasks:
        complete_task(task, user, notes=reason or "Audit prep avviato.")
        closed += 1
    return closed


def sync_program_completion(program) -> float:
    """Ricalcola % completamento del programma dai AuditPrep reali."""
    audits = list(program.planned_audits)
    total = len(audits)
    completed = 0

    for audit in audits:
        prep_id = audit.get("audit_prep_id")
        if not prep_id:
            continue
        prep = AuditPrep.objects.filter(pk=prep_id).first()
        if not prep:
            continue
        if prep.status == "completato":
            audit["status"] = "completed"
            completed += 1
        elif prep.status == "in_corso":
            audit["status"] = "in_progress"
        elif prep.status == "archiviato":
            audit["status"] = "cancelled"

    program.planned_audits = audits
    pct = round(completed / total * 100, 1) if total > 0 else 0
    if pct == 100:
        program.status = "completato"
    elif completed > 0:
        program.status = "in_corso"
    program.save(update_fields=["planned_audits", "status", "updated_at"])
    return pct


def count_overdue_program_audits_by_plant():
    """Conta gli audit pianificati **in ritardo** dei programmi annuali attivi, per plant.

    Service canonico riusato dal Centro Operativo (M21). Un audit è in ritardo
    quando la sua `planned_date` è già passata e non è ancora stato chiuso
    (`status` non in `completed`/`cancelled`). Si considerano solo i programmi
    attivi (`approvato`/`in_corso`): bozze e programmi completati non generano
    rumore. ISO 27001 §9.2.

    Ritorna una lista `[{"plant_id": <uuid str>, "c": <conteggio>}]` (solo > 0),
    nello stesso formato atteso da `_per_plant` degli advisor.
    """
    today = str(timezone.localdate())
    tally = {}
    qs = AuditProgram.objects.filter(
        status__in=["approvato", "in_corso"], deleted_at__isnull=True,
    ).only("plant_id", "planned_audits")
    for program in qs:
        if not program.plant_id:
            continue
        overdue = sum(
            1 for a in (program.planned_audits or [])
            if a.get("status") not in ("completed", "cancelled")
            and a.get("planned_date", "") and a.get("planned_date") < today
        )
        if overdue:
            tally[str(program.plant_id)] = tally.get(str(program.plant_id), 0) + overdue
    return [{"plant_id": pid, "c": c} for pid, c in tally.items()]
