import datetime
import hashlib
import uuid

from django.utils import timezone
from core.audit import log_action

from .models import AuditPrep, AuditFinding

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
    """Calculate readiness score 0-100 based on evidence_items status."""
    items = list(audit_prep.evidence_items.all())
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


def open_finding(audit_prep, finding_type: str, title: str,
                 description: str, audit_date, user,
                 control_instance=None,
                 auditor_name: str = "",
                 auto_generated: bool = False) -> AuditFinding:
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
            base_date = audit_date if hasattr(audit_date, "year") else timezone.now().date()
            deadline = get_due_date(rule_type, plant=audit_prep.plant, from_date=base_date)
        except Exception:
            deadline_days = DEADLINE_DAYS.get(finding_type)
            if deadline_days:
                base_date = audit_date if hasattr(audit_date, "year") else timezone.now().date()
                deadline = base_date + datetime.timedelta(days=deadline_days)

    finding = AuditFinding.objects.create(
        audit_prep=audit_prep,
        control_instance=control_instance,
        finding_type=finding_type,
        title=title,
        description=description,
        auditor_name=auditor_name,
        audit_date=audit_date,
        response_deadline=deadline,
        status="open",
        auto_generated=auto_generated,
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
    except Exception:
        pass

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


def close_finding(finding: AuditFinding, user,
                  closure_notes: str = "",
                  evidence=None) -> AuditFinding:
    """
    Chiude un AuditFinding.
    Richiede evidenza per major e minor NC.
    Crea automaticamente Lesson Learned.
    Aggiorna ControlInstance se collegato.
    """
    from django.core.exceptions import ValidationError

    if finding.finding_type in ("major_nc", "minor_nc"):
        if evidence is None:
            raise ValidationError(
                f"Per {finding.finding_type} e' obbligatoria "
                f"un'evidenza di chiusura."
            )
        if not closure_notes or len(closure_notes.strip()) < 20:
            raise ValidationError(
                "Le note di chiusura devono essere almeno 20 caratteri."
            )

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

    # Chiudi PDCA collegato se esiste
    if finding.pdca_cycle and finding.pdca_cycle.fase_corrente != "chiuso":
        from apps.pdca.services import close_cycle
        close_cycle(finding.pdca_cycle, user)

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
    from apps.controls.models import ControlInstance
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


def launch_audit_from_program(program, audit_entry: dict, user) -> "AuditPrep":
    """
    Crea un AuditPrep collegato a un audit pianificato nel programma annuale.
    Precompila gli EvidenceItem in base ai domini e coverage_type.
    Atomico: se un qualsiasi passo fallisce nessun record viene persistito.
    """
    import random as _rnd
    from django.db import transaction
    from django.db.models import Q
    from apps.controls.models import ControlInstance, Framework
    from .models import EvidenceItem

    with transaction.atomic():
        fw_codes = audit_entry.get("framework_codes", [])
        frameworks = list(Framework.objects.filter(code__in=fw_codes))
        primary_fw = frameworks[0] if frameworks else None

        prep = AuditPrep.objects.create(
            plant=program.plant,
            framework=primary_fw,
            title=audit_entry["title"],
            audit_date=audit_entry.get("planned_date") or None,
            auditor_name=audit_entry.get("auditor_name", ""),
            status="in_corso",
            audit_program=program,
            audit_entry_id=audit_entry["id"],
            coverage_type=audit_entry.get("coverage_type", "campione"),
            created_by=user,
        )

        scope_domains = audit_entry.get("scope_domains", [])
        coverage_type = audit_entry.get("coverage_type", "campione")

        # Seed deterministico: stessa selezione campione per questo audit
        seed_str = f"{program.pk}-{audit_entry.get('quarter', 1)}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2 ** 31)
        rng = _rnd.Random(seed)

        items_to_create = []
        for fw in frameworks:
            instances = ControlInstance.objects.filter(
                plant=program.plant,
                control__framework=fw,
                deleted_at__isnull=True,
            ).select_related("control__domain")

            if scope_domains:
                # Fix 3: fallback a external_id se domain.code è None
                instances = instances.filter(
                    Q(control__domain__code__in=scope_domains) |
                    Q(control__domain__external_id__in=scope_domains)
                )

            instance_list = list(instances)

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

            for inst in instance_list:
                items_to_create.append(EvidenceItem(
                    audit_prep=prep,
                    control_instance=inst,
                    description=(
                        f"{inst.control.external_id} — "
                        f"{inst.control.get_title('it')}"
                    ),
                    status="mancante",
                    created_by=user,
                ))

        # Un singolo INSERT invece di N INSERT separati
        EvidenceItem.objects.bulk_create(items_to_create, ignore_conflicts=True)

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

        log_action(
            user=user,
            action_code="audit_prep.launched_from_program",
            level="L2",
            entity=prep,
            payload={
                "program_id": str(program.pk),
                "quarter": audit_entry["quarter"],
                "coverage": coverage_type,
                "controls_count": len(items_to_create),
            },
        )
    return prep


def generate_audit_report(prep: "AuditPrep") -> str:
    """Genera relazione HTML scaricabile dell'audit."""
    plant_name = prep.plant.name if prep.plant else "—"
    fw_name = prep.framework.name if prep.framework else "—"
    auditor = prep.auditor_name or "—"
    audit_date = prep.audit_date.strftime("%d/%m/%Y") if prep.audit_date else "—"
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
