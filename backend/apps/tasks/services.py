import datetime

from django.db import transaction
from django.utils import timezone

from core.audit import log_action

from .models import Task


def create_task(
    plant,
    title,
    description="",
    priority="media",
    source_module="M03",
    source_id=None,
    due_date=None,
    assign_type=None,
    assign_value=None,
    control_instance=None,
):
    """Crea un Task collegato a un modulo sorgente."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    assigned_to = None
    if assign_type == "user" and assign_value:
        assigned_to = User.objects.filter(pk=assign_value).first()

    # Mappa source_module al campo source
    source_map = {
        "M03": "controllo", "M06": "rischio", "M09": "incidente",
        "M11": "pdca", "M17": "audit",
    }
    source = source_map.get(source_module, "manuale")

    return Task.objects.create(
        title=title,
        description=description,
        plant=plant,
        priority=priority,
        source=source,
        source_module=source_module or "",
        source_id=source_id,
        assigned_to=assigned_to,
        assigned_role=assign_value if assign_type == "role" else "",
        due_date=due_date,
        control_instance=control_instance,
    )


def complete_task(task, user, notes=""):
    task.status = "completato"
    task.completed_at = timezone.now()
    task.completed_by = user
    if notes:
        task.notes = (task.notes + "\n" + notes).strip()
    task.save(
        update_fields=["status", "completed_at", "completed_by", "notes", "updated_at"]
    )
    log_action(
        user=user,
        action_code="task.completed",
        level="L1",
        entity=task,
        payload={"id": str(task.pk), "title": task.title},
    )
    if task.recurrence != "none":
        _spawn_next_recurrence(task)


def _spawn_next_recurrence(task):
    deltas = {
        "daily": datetime.timedelta(days=1),
        "weekly": datetime.timedelta(weeks=1),
        "monthly": datetime.timedelta(days=30),
        "quarterly": datetime.timedelta(days=90),
        "yearly": datetime.timedelta(days=365),
    }
    delta = deltas.get(task.recurrence)
    if not delta or not task.due_date:
        return
    Task.objects.create(
        title=task.title,
        description=task.description,
        plant=task.plant,
        priority=task.priority,
        source=task.source,
        assigned_role=task.assigned_role,
        assigned_to=task.assigned_to,
        due_date=task.due_date + delta,
        recurrence=task.recurrence,
        parent_task=task,
        control_instance=task.control_instance,
        incident=task.incident,
    )


def escalate_task(task, user):
    task.escalation_level += 1
    task.escalated_at = timezone.now()
    task.save(update_fields=["escalation_level", "escalated_at", "updated_at"])
    log_action(
        user=user,
        action_code="task.escalated",
        level="L2",
        entity=task,
        payload={
            "id": str(task.pk),
            "title": task.title,
            "escalation_level": task.escalation_level,
        },
    )


def get_overdue_tasks(plant_id=None):
    qs = Task.objects.filter(
        status__in=["aperto", "in_corso"], due_date__lt=timezone.localdate()
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    return qs.select_related("plant", "assigned_to")


# ── Quick Checklist (M08) ────────────────────────────────────────────────────

# Soglia: N run consecutivi incompleti su uno stesso template apre un PDCA (M11).
CHECKLIST_PDCA_THRESHOLD = 3


def _run_has_unchecked_mandatory(run) -> bool:
    """Vero se il run ha almeno un item obbligatorio non spuntato."""
    return run.items.filter(
        template_item__is_mandatory=True, checked=False
    ).exists()


def create_run_for_template(template, plant, due_date):
    """
    Crea un ChecklistRun per (template, plant, due_date) con un RunItem per
    ciascun item attivo del template. Idempotente: non duplica un run esistente.
    """
    from .models import ChecklistRun, ChecklistRunItem

    existing = ChecklistRun.objects.filter(
        template=template, plant=plant, due_date=due_date
    ).first()
    if existing:
        return existing

    run = ChecklistRun.objects.create(
        template=template,
        plant=plant,
        due_date=due_date,
        status="pending",
    )
    items = [
        ChecklistRunItem(run=run, template_item=ti)
        for ti in template.items.all()
    ]
    if items:
        ChecklistRunItem.objects.bulk_create(items)
    return run


def complete_run_item(
    run, item_id, checked, note="", user=None, value=None, text_value=None
):
    """Compila un singolo item del run. Nessun workflow, immediato.
    `value`/`text_value` sono valorizzati per gli item numeric/text (KPI)."""
    run_item = run.items.filter(pk=item_id).first()
    if run_item is None:
        return None
    run_item.checked = bool(checked)
    run_item.note = note or ""
    if value is not None:
        run_item.value = value
    if text_value is not None:
        run_item.text_value = text_value
    update_fields = ["checked", "note", "value", "text_value", "updated_at"]
    if run_item.checked:
        run_item.checked_at = timezone.now()
        run_item.checked_by = user
    else:
        run_item.checked_at = None
        run_item.checked_by = None
    update_fields += ["checked_at", "checked_by"]
    run_item.save(update_fields=update_fields)

    # Primo check/compilazione → il run passa a in_progress
    if run.status == "pending" and run.items.filter(checked=True).exists():
        run.status = "in_progress"
        run.save(update_fields=["status", "updated_at"])
    return run_item


def complete_run(run, user):
    """
    Marca il run come completato — solo se tutti gli item obbligatori sono
    spuntati. Registra l'audit trail seguendo il pattern degli altri moduli.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    if _run_has_unchecked_mandatory(run):
        raise ValidationError(
            _("Tutti gli item obbligatori devono essere spuntati prima di completare.")
        )

    with transaction.atomic():
        run.status = "completed"
        run.completed_at = timezone.now()
        run.completed_by = user
        run.save(update_fields=["status", "completed_at", "completed_by", "updated_at"])

        log_action(
            user=user,
            action_code="checklist_run.completed",
            level="L1",
            entity=run,
            payload={
                "id": str(run.pk),
                "template": run.template.name,
                "plant_id": str(run.plant_id),
                "items_total": run.items.count(),
                "items_checked": run.items.filter(checked=True).count(),
            },
        )
    return run


def evaluate_checklist_pdca_threshold(template, user=None):
    """
    Se gli ultimi CHECKLIST_PDCA_THRESHOLD run conclusi (completed/overdue) di
    un template hanno tutti almeno un item obbligatorio non spuntato, apre
    automaticamente un ciclo PDCA (M11) collegato al template.
    Idempotente: non crea un nuovo ciclo se ne esiste già uno aperto.
    """
    from apps.pdca.models import PdcaCycle
    from apps.pdca.services import create_cycle

    from .models import ChecklistRun

    recent = list(
        ChecklistRun.objects.filter(
            template=template, status__in=["completed", "overdue"]
        )
        .select_related("plant")
        .prefetch_related("items")
        .order_by("-due_date", "-created_at")[:CHECKLIST_PDCA_THRESHOLD]
    )
    if len(recent) < CHECKLIST_PDCA_THRESHOLD:
        return None
    if not all(_run_has_unchecked_mandatory(r) for r in recent):
        return None

    # Evita duplicati: un solo ciclo aperto per template alla volta.
    already_open = PdcaCycle.objects.filter(
        trigger_type="checklist_incompleta",
        trigger_source_id=template.pk,
        deleted_at__isnull=True,
    ).exclude(fase_corrente__in=["chiuso", "archiviato"]).exists()
    if already_open:
        return None

    plant = template.plant or recent[0].plant
    return create_cycle(
        plant=plant,
        title=f"Checklist ricorrente incompleta: {template.name}",
        trigger_type="checklist_incompleta",
        trigger_source_id=template.pk,
    )


# ── KPI Engine operativo (M08 ↔ M18) ─────────────────────────────────────────

# Ranking di severità per capire se uno stato è peggiorato (trigger alert).
_KPI_STATUS_RANK = {"no_data": 0, "ok": 1, "warning": 2, "critical": 3}


def _monday_of(d: datetime.date) -> datetime.date:
    """Lunedì della settimana che contiene la data `d`."""
    return d - datetime.timedelta(days=d.weekday())


def _kpi_status_worsened(old_status, new_status) -> bool:
    """
    Vero se `new_status` è più grave di `old_status`. Se non esiste uno stato
    precedente si assume 'ok' come baseline (così il primo warning/critical
    genera comunque alert). 'no_data' non è mai un peggioramento.
    """
    if new_status == "no_data":
        return False
    baseline = _KPI_STATUS_RANK.get(old_status, _KPI_STATUS_RANK["ok"])
    return _KPI_STATUS_RANK.get(new_status, 0) > baseline


def calculate_kpi_value(kpi_def, plant, week_start) -> dict:
    """
    Calcola il valore del KPI (source=checklist) per la settimana indicata.
    Ritorna {"value": float|None, "run_count": int, "note": str}.

    Considera i ChecklistRun del template nel range [week_start, week_start+6gg]
    per il plant indicato, in stato completed o overdue.
    """
    from django.db.models import Avg

    from .models import ChecklistRun, ChecklistRunItem

    if kpi_def.source != "checklist" or not kpi_def.checklist_template_id:
        return {
            "value": None,
            "run_count": 0,
            "note": "KPI non basato su checklist: valore atteso via ingest API.",
        }

    week_end = week_start + datetime.timedelta(days=6)
    runs = ChecklistRun.objects.filter(
        template_id=kpi_def.checklist_template_id,
        due_date__gte=week_start,
        due_date__lte=week_end,
        status__in=["completed", "overdue"],
    )
    if plant is not None:
        runs = runs.filter(plant=plant)

    run_count = runs.count()
    if run_count == 0:
        return {"value": None, "run_count": 0, "note": "Nessun run nel periodo."}

    agg = kpi_def.aggregation

    if agg == "success_rate":
        completed = runs.filter(status="completed").count()
        value = round(completed / run_count * 100, 2)
        return {
            "value": value,
            "run_count": run_count,
            "note": f"{completed}/{run_count} run completati",
        }

    # Aggregazioni a livello item: filtra gli item dei run nel periodo.
    items = ChecklistRunItem.objects.filter(run__in=runs)
    if kpi_def.checklist_item_filter:
        items = items.filter(
            template_item__text__icontains=kpi_def.checklist_item_filter
        )

    if agg == "avg_value":
        numeric = items.filter(template_item__item_type="numeric", value__isnull=False)
        avg = numeric.aggregate(a=Avg("value"))["a"]
        if avg is None:
            return {
                "value": None,
                "run_count": run_count,
                "note": "Nessun valore numerico registrato.",
            }
        return {
            "value": round(float(avg), 2),
            "run_count": run_count,
            "note": f"Media su {numeric.count()} valori",
        }

    if agg == "last_value":
        numeric = items.filter(template_item__item_type="numeric", value__isnull=False)
        last = numeric.order_by(
            "-run__due_date", "-checked_at", "-created_at"
        ).first()
        if last is None or last.value is None:
            return {
                "value": None,
                "run_count": run_count,
                "note": "Nessun valore numerico registrato.",
            }
        return {
            "value": float(last.value),
            "run_count": run_count,
            "note": "Ultimo valore registrato nel periodo",
        }

    if agg == "count_ok":
        n = items.filter(checked=True).count()
        return {"value": float(n), "run_count": run_count, "note": f"{n} item OK"}

    if agg == "count_fail":
        n = items.filter(checked=False).count()
        return {"value": float(n), "run_count": run_count, "note": f"{n} item KO"}

    return {"value": None, "run_count": run_count, "note": "Aggregazione sconosciuta."}


def evaluate_kpi_status(kpi_def, value) -> str:
    """
    Ritorna "ok" | "warning" | "critical" | "no_data".
    threshold_direction='above' → valori alti sono buoni (es. success_rate):
    scendere sotto warning/critical è negativo.
    threshold_direction='below' → valori bassi sono buoni (es. vuln aperte):
    salire sopra warning/critical è negativo.
    """
    if value is None:
        return "no_data"

    warn = kpi_def.threshold_warning
    crit = kpi_def.threshold_critical
    if warn is None and crit is None:
        return "ok"

    if kpi_def.threshold_direction == "above":
        if crit is not None and value < crit:
            return "critical"
        if warn is not None and value < warn:
            return "warning"
        return "ok"
    else:  # below
        if crit is not None and value > crit:
            return "critical"
        if warn is not None and value > warn:
            return "warning"
        return "ok"


def _maybe_alert(kpi_def, plant, snapshot, prev_status) -> bool:
    """Invia alert se lo status è peggiorato e la notifica è abilitata.
    Ritorna True se un alert è stato effettivamente inviato."""
    if not _kpi_status_worsened(prev_status, snapshot.status):
        return False
    if snapshot.status == "warning" and kpi_def.notify_on_warning:
        _send_kpi_alert(kpi_def, plant, snapshot)
        return True
    if snapshot.status == "critical" and kpi_def.notify_on_critical:
        _send_kpi_alert(kpi_def, plant, snapshot)
        return True
    return False


def compute_and_store_kpi_snapshot(kpi_def, plant, week_start):
    """
    Calcola e salva (o aggiorna) l'OperationalKpiSnapshot per (kpi, plant,
    settimana). Se lo status è peggiorato rispetto allo snapshot precedente e
    le notifiche sono abilitate, invia l'alert via M19.
    """
    from .models import OperationalKpiSnapshot

    result = calculate_kpi_value(kpi_def, plant, week_start)
    value = result["value"]
    status = evaluate_kpi_status(kpi_def, value)

    prev = (
        OperationalKpiSnapshot.objects.filter(
            kpi_definition=kpi_def, plant=plant, week_start__lt=week_start
        )
        .order_by("-week_start")
        .first()
    )
    prev_status = prev.status if prev else None

    snapshot, _created = OperationalKpiSnapshot.objects.update_or_create(
        kpi_definition=kpi_def,
        plant=plant,
        week_start=week_start,
        defaults={
            "value": value,
            "status": status,
            "source": kpi_def.source,
            "measured_at": timezone.now(),
            "run_count": result["run_count"],
            "note": result["note"],
        },
    )

    # Espone al chiamante (es. task Celery) se è stato inviato un alert, senza
    # alterare il valore di ritorno documentato (lo snapshot).
    snapshot._alert_sent = _maybe_alert(kpi_def, plant, snapshot, prev_status)
    return snapshot


def _send_kpi_alert(kpi_def, plant, snapshot):
    """
    Invia la notifica di alert KPI via M19. Destinatari: utenti con ruolo
    Plant Manager o Compliance Officer (responsabilità CISO/sicurezza in questo
    modello di ruoli) con accesso al plant. Per KPI globali (plant=None) tutti
    i titolari di quei ruoli. Non logga indirizzi email (regola #11).
    """
    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.notifications.resolver import _user_has_access_to_plant
    from apps.notifications.services import notify_kpi_alert

    roles = [GrcRole.PLANT_MANAGER, GrcRole.COMPLIANCE_OFFICER]
    qs = (
        UserPlantAccess.objects.filter(role__in=roles, deleted_at__isnull=True)
        .select_related("user", "scope_bu")
        .prefetch_related("scope_plants")
    )
    emails: set[str] = set()
    for access in qs:
        if not access.user.is_active or not access.user.email:
            continue
        if plant is None or _user_has_access_to_plant(access, plant):
            emails.add(access.user.email)

    if emails:
        notify_kpi_alert(kpi_def, plant, snapshot, sorted(emails))


def _resolve_audit_user(user):
    """
    Restituisce un utente a cui attribuire l'audit. Per le ingestioni via API
    key (senza utente) ripiega sul primo superuser attivo. Può essere None se
    il sistema non ha alcun superuser (caso limite): in tal caso l'audit viene
    saltato dal chiamante.
    """
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(
        is_superuser=True, is_active=True
    ).order_by("date_joined").first()


def ingest_kpi_from_api(
    kpi_code, plant_id, value, source, measured_at=None, note="", user=None
):
    """
    Entry point per l'ingestione di un KPI da sorgente esterna (API/script).
    Trova o crea la KPIDefinition (source=api) per kpi_code, salva lo snapshot
    settimanale, valuta lo status, invia alert se necessario e registra
    l'azione nell'audit trail.
    """
    from apps.plants.models import Plant

    from .models import KPIDefinition, OperationalKpiSnapshot

    measured_at = measured_at or timezone.now()
    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None

    kpi_def, _created = KPIDefinition.objects.get_or_create(
        kpi_code=kpi_code,
        defaults={
            "name": kpi_code.replace("_", " ").title(),
            "source": "api",
            "plant": plant,
        },
    )

    measured_date = measured_at.date() if hasattr(measured_at, "date") else measured_at
    week_start = _monday_of(measured_date)
    value_f = float(value) if value is not None else None
    status = evaluate_kpi_status(kpi_def, value_f)

    prev = (
        OperationalKpiSnapshot.objects.filter(
            kpi_definition=kpi_def, plant=plant, week_start__lt=week_start
        )
        .order_by("-week_start")
        .first()
    )
    prev_status = prev.status if prev else None

    note_label = (note or "").strip()
    note_full = f"{note_label} [origine: {source}]".strip() if source else note_label

    snapshot, _c = OperationalKpiSnapshot.objects.update_or_create(
        kpi_definition=kpi_def,
        plant=plant,
        week_start=week_start,
        defaults={
            "value": value_f,
            "status": status,
            "source": "api",
            "measured_at": measured_at,
            "run_count": 0,
            "note": note_full[:2000],
        },
    )

    _maybe_alert(kpi_def, plant, snapshot, prev_status)

    audit_user = _resolve_audit_user(user)
    if audit_user is not None:
        log_action(
            user=audit_user,
            action_code="kpi.ingested",
            level="L1",
            entity=snapshot,
            payload={
                "kpi_code": kpi_code,
                "origin": str(source)[:50],
                "value": value_f,
                "status": status,
                "plant_id": str(plant.id) if plant else None,
                "week_start": week_start.isoformat(),
            },
        )
    return snapshot


def create_template_from_seed(code, plant, user=None, lang="it"):
    """
    Crea (o riusa) un ChecklistTemplate "scheletro" a partire dal template_seed
    del catalogo per il kpi_code indicato. Idempotente: se esiste già un template
    con lo stesso nome per quel plant lo riusa. Ritorna il template o None se il
    KPI non ha un seed.
    """
    from .kpi_catalog import KPI_CATALOG, _text
    from .models import ChecklistTemplate, ChecklistTemplateItem

    entry = KPI_CATALOG.get(code)
    seed = entry.get("template_seed") if entry else None
    if not seed:
        return None

    name = _text(seed["name"], lang)
    existing = ChecklistTemplate.objects.filter(
        name=name, plant=plant, deleted_at__isnull=True
    ).first()
    if existing:
        return existing

    template = ChecklistTemplate.objects.create(
        name=name,
        description="",
        frequency=seed.get("frequency", "daily"),
        plant=plant,
        is_active=True,
        created_by=user,
    )
    ChecklistTemplateItem.objects.bulk_create([
        ChecklistTemplateItem(
            template=template,
            order=idx,
            text=_text(item["text"], lang),
            is_mandatory=item.get("is_mandatory", True),
            item_type=item.get("item_type", "checkbox"),
            unit=item.get("unit", ""),
        )
        for idx, item in enumerate(seed.get("items", []))
    ])
    if user is not None:
        log_action(
            user=user,
            action_code="checklist_template.created",
            level="L1",
            entity=template,
            payload={
                "id": str(template.pk),
                "name": template.name,
                "from_kpi_seed": code,
            },
        )
    return template


def import_kpi_suggestions(plant, kpi_codes, overrides=None, user=None) -> dict:
    """
    Importa una lista di KPI dal catalogo standard (kpi_catalog.KPI_CATALOG)
    applicando eventuali override per soglie/template. Idempotente: i KPI il
    cui kpi_code esiste già vengono saltati. Ritorna {created, skipped, errors}.

    Override per kpi_code:
      - threshold_warning / threshold_critical: soglie personalizzate
      - checklist_template: UUID di un template esistente da collegare
      - create_template: True → crea il template dallo seed del catalogo
    """
    from .kpi_catalog import KPI_CATALOG, _text
    from .models import ChecklistTemplate, KPIDefinition

    overrides = overrides or {}
    created, skipped, errors = [], [], []

    for code in kpi_codes:
        entry = KPI_CATALOG.get(code)
        if entry is None:
            errors.append({"kpi_code": code, "error": "not_in_catalog"})
            continue
        # Idempotenza: kpi_code è unique a livello di sistema.
        if KPIDefinition.objects.filter(kpi_code=code).exists():
            skipped.append(code)
            continue

        ov = overrides.get(code, {}) or {}
        template = None
        tpl_id = ov.get("checklist_template")
        if tpl_id:
            template = ChecklistTemplate.objects.filter(pk=tpl_id).first()
        elif ov.get("create_template") and entry.get("template_seed"):
            template = create_template_from_seed(code, plant, user=user)

        def _ov_threshold(key, ov=ov, entry=entry):
            # default-bind: la closure non deve catturare le variabili di loop
            return ov[key] if key in ov else entry[key]

        try:
            kpi = KPIDefinition.objects.create(
                kpi_code=code,
                name=_text(entry["name"], "it"),
                description=_text(entry["description"], "it"),
                unit=entry["unit"],
                source=entry["source"],
                checklist_template=template,
                checklist_item_filter="",
                aggregation=entry["aggregation"],
                plant=plant,
                threshold_warning=_ov_threshold("threshold_warning"),
                threshold_critical=_ov_threshold("threshold_critical"),
                threshold_direction=entry["threshold_direction"],
                is_active=True,
                notify_on_warning=entry["notify_on_warning"],
                notify_on_critical=entry["notify_on_critical"],
                created_by=user,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append({"kpi_code": code, "error": str(exc)[:200]})
            continue

        if user is not None:
            log_action(
                user=user,
                action_code="kpi_definition.imported",
                level="L1",
                entity=kpi,
                payload={
                    "kpi_code": code,
                    "plant_id": str(plant.id) if plant else None,
                    "source": entry["source"],
                    "from_catalog": True,
                },
            )
        created.append(code)

    return {"created": created, "skipped": skipped, "errors": errors}
