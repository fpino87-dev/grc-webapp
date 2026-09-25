"""Business logic modulo OSINT.

Aggregator (Step 2): legge dagli altri moduli e popola `OsintEntity`.
Nessuna logica di enrichment o scoring qui — vedi `enrichers/`, `scoring.py`, `alerts.py`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from django.db import transaction

from apps.assets.models import AssetIT, AssetOT, AssetSW
from apps.plants.models import Plant
from apps.suppliers.models import Supplier

from .models import (
    EntityType,
    OsintEntity,
    OsintSettings,
    SourceModule,
)

from .validators import hostname_is_scannable, is_public_mail_domain

logger = logging.getLogger(__name__)


def domain_from_email(email: str | None) -> str:
    """Estrae il dominio da un indirizzo email. 'user@example.com' → 'example.com'."""
    if not email or "@" not in email:
        return ""
    return email.strip().split("@")[-1].lower().strip()


def extract_domain(raw: str | None) -> str:
    """Estrae l'hostname (lowercase) da una URL o stringa dominio.

    Esempi:
      "https://example.com/path" → "example.com"
      "example.COM" → "example.com"
      "" → ""
      None → ""
    """
    if not raw:
        return ""
    value = raw.strip()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    try:
        host = urlparse(value).hostname or ""
    except ValueError:
        return ""
    return host.lower().rstrip(".")


@dataclass
class AggregationResult:
    created: int = 0
    updated: int = 0
    reactivated: int = 0
    deactivated: int = 0
    skipped: int = 0

    def add(self, other: "AggregationResult") -> "AggregationResult":
        self.created += other.created
        self.updated += other.updated
        self.reactivated += other.reactivated
        self.deactivated += other.deactivated
        self.skipped += other.skipped
        return self


def _upsert_entity(
    *,
    source_module: str,
    source_id,
    domain: str,
    entity_type: str,
    display_name: str,
    is_nis2_critical: bool,
    scan_frequency: str,
    result: AggregationResult,
    kept: set,
    extra: dict | None = None,
) -> None:
    domain = domain.strip().lower()
    if not domain:
        return

    # Hostname interni e TLD riservati non potranno mai essere scansionati:
    # censirli crea entità che restano per sempre senza dati, e senza che
    # nulla lo segnali.
    scannable, reason = hostname_is_scannable(domain)
    if not scannable:
        logger.info(
            "OSINT: dominio '%s' ignorato in ingestione (%s) — sorgente %s",
            domain, reason, source_module,
        )
        result.skipped += 1
        return

    entity, created = OsintEntity.objects.get_or_create(
        source_module=source_module,
        source_id=source_id,
        domain=domain,
        defaults={
            "entity_type": entity_type,
            "display_name": display_name,
            "is_nis2_critical": is_nis2_critical,
            "scan_frequency": scan_frequency,
            "is_active": True,
            **(extra or {}),
        },
    )
    if created:
        result.created += 1
    else:
        changed = False
        if entity.entity_type != entity_type:
            entity.entity_type = entity_type
            changed = True
        if entity.display_name != display_name:
            entity.display_name = display_name
            changed = True
        if entity.is_nis2_critical != is_nis2_critical:
            entity.is_nis2_critical = is_nis2_critical
            changed = True
        if entity.scan_frequency != scan_frequency:
            entity.scan_frequency = scan_frequency
            changed = True
        if not entity.is_active:
            entity.is_active = True
            result.reactivated += 1
            changed = True
        for field, value in (extra or {}).items():
            if getattr(entity, field) != value:
                setattr(entity, field, value)
                changed = True
        if changed:
            entity.save()
            result.updated += 1
    if created:
        _mark_duplicate_candidate(entity)
    kept.add(entity.pk)


def _counterpart_domain(domain: str) -> str:
    """`www.X` ↔ `X`. Stringa vuota se non c'è una controparte sensata."""
    if domain.startswith("www."):
        return domain[4:]
    # Solo per i domini apex: aggiungere "www." a un sottodominio qualsiasi
    # (es. api.example.com) non produce una controparte plausibile.
    return f"www.{domain}" if domain.count(".") == 1 else ""


def _mark_duplicate_candidate(entity) -> None:
    """
    Registra il sospetto che `www.X` e `X` siano la stessa proprietà web.

    Sospetto, non certezza: possono risolvere altrove, servire contenuti
    diversi o esistere solo uno dei due. Qui si annota soltanto; la verifica
    (`verify_duplicate_candidate`) conferma o smentisce, e l'eventuale unione
    resta una decisione umana.
    """
    counterpart_domain = _counterpart_domain(entity.domain)
    if not counterpart_domain:
        return
    counterpart = (
        OsintEntity.objects.filter(domain=counterpart_domain, is_active=True)
        .exclude(pk=entity.pk)
        .first()
    )
    if counterpart is None:
        return
    entity.duplicate_candidate_of = counterpart
    entity.duplicate_verified = None
    entity.save(update_fields=["duplicate_candidate_of", "duplicate_verified", "updated_at"])


def verify_duplicate_candidate(entity) -> bool | None:
    """
    Confronta gli indirizzi di `www.X` e `X`: stessi IP = alias, IP diversi =
    proprietà distinte, irrisolvibile = si resta nel dubbio (None).

    Non modifica nulla oltre all'esito: nessuna entità viene unita o
    disattivata: quella scelta è di chi conosce l'infrastruttura.
    """
    from apps.osint.validators import _resolve_all

    other = entity.duplicate_candidate_of
    if other is None:
        return None
    mine = set(_resolve_all(entity.domain) or [])
    theirs = set(_resolve_all(other.domain) or [])
    if not mine or not theirs:
        verdict = None
    else:
        verdict = bool(mine & theirs)
    entity.duplicate_verified = verdict
    entity.save(update_fields=["duplicate_verified", "updated_at"])
    return verdict


def _deactivate_missing(source_module: str, kept: set, result: AggregationResult) -> None:
    """Disattiva entità non più presenti nella sorgente.

    Itera e salva per ognuna invece di `qs.update()` per rispettare il pattern
    di soft-delete/audit (regola architetturale CLAUDE.md #5).
    """
    qs = OsintEntity.objects.filter(source_module=source_module, is_active=True).exclude(pk__in=kept)
    for entity in qs.iterator():
        entity.is_active = False
        entity.save(update_fields=["is_active", "updated_at"])
        result.deactivated += 1


def _sync_plants(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for plant in Plant.objects.all():  # soft-delete manager filtra già deleted_at
        domains: list[str] = []
        if plant.domain:
            domains.append(plant.domain)
        for d in plant.additional_domains or []:
            if d:
                domains.append(d)
        for raw in domains:
            domain = extract_domain(raw)
            if not domain:
                continue
            _upsert_entity(
                source_module=SourceModule.SITES,
                source_id=plant.id,
                domain=domain,
                entity_type=EntityType.MY_DOMAIN,
                display_name=plant.name,
                is_nis2_critical=plant.is_nis2_subject,
                scan_frequency=settings.freq_my_domains,
                result=result,
                kept=kept,
            )
    _deactivate_missing(SourceModule.SITES, kept, result)


def supplier_is_critical(sup, ot_maintainers: set) -> bool:
    """Fornitore critico → monitoraggio approfondito: rilevante NIS2 o TISAX,
    rischio alto/critico (dichiarato, rettificato o da valutazione interna),
    oppure manutentore di asset OT."""
    risky = {"alto", "critico"}
    return bool(
        getattr(sup, "nis2_relevant", False) or getattr(sup, "tisax_relevant", False)
        or {getattr(sup, "risk_level", ""), getattr(sup, "risk_adj", ""), getattr(sup, "internal_risk_level", "")} & risky
        or sup.pk in ot_maintainers
    )


def service_hosts_from(urls) -> list[str]:
    """Host dei servizi del fornitore usati da noi (da URL o hostname)."""
    hosts = []
    for raw in urls or []:
        host = extract_domain(str(raw))
        if host and host not in hosts and hostname_is_scannable(host)[0]:
            hosts.append(host)
    return hosts[:10]


def _sync_suppliers(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    ot_maintainers = set(
        AssetOT.objects.filter(maintainer_supplier__isnull=False).values_list("maintainer_supplier_id", flat=True)
    )
    for sup in Supplier.objects.all():
        # Il ripiego sull'email vale solo se il dominio è del fornitore: con un
        # contatto su Gmail o su una PEC si finirebbe a monitorare il provider.
        domain = extract_domain(sup.website)
        if not domain:
            candidate = domain_from_email(sup.email)
            domain = "" if is_public_mail_domain(candidate) else candidate
        if not domain:
            continue
        is_nis2 = bool(getattr(sup, "nis2_relevant", False))
        deep = supplier_is_critical(sup, ot_maintainers)
        freq = settings.freq_suppliers_critical if deep else settings.freq_suppliers_other
        _upsert_entity(
            source_module=SourceModule.SUPPLIERS,
            source_id=sup.id,
            domain=domain,
            entity_type=EntityType.SUPPLIER,
            display_name=sup.name,
            is_nis2_critical=is_nis2,
            scan_frequency=freq,
            result=result,
            kept=kept,
            extra={"deep_monitoring": deep, "service_hosts": service_hosts_from(getattr(sup, "service_urls", None))},
        )
    _deactivate_missing(SourceModule.SUPPLIERS, kept, result)


def _sync_assets_it(settings: OsintSettings, result: AggregationResult) -> None:
    from .validators import is_public_internet_target

    kept: set = set()
    for a in AssetIT.objects.select_related("plant").all():
        candidates: list[str] = []
        if a.fqdn:
            candidates.append(a.fqdn)
        if a.ip_address:
            candidates.append(str(a.ip_address))
        for raw in candidates:
            domain = extract_domain(raw)
            if not domain:
                continue
            if not is_public_internet_target(domain):
                logger.debug("OSINT: skipping non-public asset domain %s (%s)", domain, a.name)
                continue
            _upsert_entity(
                source_module=SourceModule.ASSETS_IT,
                source_id=a.id,
                domain=domain,
                entity_type=EntityType.ASSET,
                display_name=a.name,
                is_nis2_critical=False,
                scan_frequency=settings.freq_my_domains,
                result=result,
                kept=kept,
            )
    _deactivate_missing(SourceModule.ASSETS_IT, kept, result)


def _sync_assets_ot(settings: OsintSettings, result: AggregationResult) -> None:
    """Sincronizza gli AssetOT *raggiungibili da Internet* come entità OSINT.

    Un asset OT non è normalmente esposto (sta dietro le zone Purdue); quando
    però ha un'interfaccia pubblica (fqdn/ip di management o teleassistenza) è
    proprio il target che vogliamo monitorare. Sincronizziamo solo gli asset
    con un target pubblico valido, con la stessa guardia
    `is_public_internet_target` usata per gli asset IT.
    """
    from .validators import is_public_internet_target

    kept: set = set()
    for a in AssetOT.objects.select_related("plant").all():
        candidates: list[str] = []
        if a.fqdn:
            candidates.append(a.fqdn)
        if a.ip_address:
            candidates.append(str(a.ip_address))
        for raw in candidates:
            domain = extract_domain(raw)
            if not domain:
                continue
            if not is_public_internet_target(domain):
                logger.debug("OSINT: skipping non-public OT asset domain %s (%s)", domain, a.name)
                continue
            _upsert_entity(
                source_module=SourceModule.ASSETS_OT,
                source_id=a.id,
                domain=domain,
                entity_type=EntityType.ASSET,
                display_name=a.name,
                is_nis2_critical=False,
                scan_frequency=settings.freq_my_domains,
                result=result,
                kept=kept,
            )
    _deactivate_missing(SourceModule.ASSETS_OT, kept, result)


def _sync_assets_software(settings: OsintSettings, result: AggregationResult) -> None:
    kept: set = set()
    for sw in AssetSW.objects.select_related("plant").all():
        domain = extract_domain(sw.vendor_url)
        if not domain:
            continue
        _upsert_entity(
            source_module=SourceModule.ASSETS_SOFTWARE,
            source_id=sw.id,
            domain=domain,
            entity_type=EntityType.SUPPLIER,  # vendor software = fornitore ai fini OSINT
            display_name=f"{sw.vendor or sw.name} ({sw.name})" if sw.vendor else sw.name,
            is_nis2_critical=False,
            scan_frequency=settings.freq_suppliers_other,
            result=result,
            kept=kept,
        )
    _deactivate_missing(SourceModule.ASSETS_SOFTWARE, kept, result)


@transaction.atomic
def aggregate_entities() -> AggregationResult:
    """Sincronizza `osint_entities` leggendo da tutti i moduli sorgente.

    Idempotente. Chiamabile ad ogni scan e all'apertura della dashboard OSINT.
    """
    settings = OsintSettings.load()
    result = AggregationResult()
    _sync_plants(settings, result)
    _sync_suppliers(settings, result)
    _sync_assets_it(settings, result)
    _sync_assets_ot(settings, result)
    _sync_assets_software(settings, result)
    logger.info(
        "OSINT aggregation completed: created=%d updated=%d reactivated=%d deactivated=%d",
        result.created, result.updated, result.reactivated, result.deactivated,
    )
    return result


def find_duplicates() -> dict[str, list[OsintEntity]]:
    """Ritorna domini presenti su più entità (più sorgenti) — per banner UI.

    Chiave: dominio; valore: lista entità attive che condividono il dominio.
    """
    from collections import defaultdict
    buckets: dict[str, list[OsintEntity]] = defaultdict(list)
    for e in OsintEntity.objects.filter(is_active=True):
        buckets[e.domain].append(e)
    return {d: items for d, items in buckets.items() if len(items) > 1}


# ---------------------------------------------------------------------------
# KPI bridge: OSINT → KPI engine M08 (→ management review M13)
# ---------------------------------------------------------------------------

OSINT_CRITICAL_KPI_CODE = "osint_critical_open_count"


def count_open_critical_findings_by_plant() -> dict[str, int]:
    """Conta i finding OSINT critici *aperti* per plant.

    Solo le entità `my_domain` mappano a un plant (`source_id` = plant pk); i
    finding di fornitori/asset non hanno un plant univoco e restano fuori da
    questo KPI per-plant. "Aperto" = stato open/acknowledged/in_progress (gli
    stati risolto/rischio-accettato non pesano sull'esposizione corrente).

    Ritorna {plant_id (str): count}, con un'entrata per ogni plant che ha almeno
    un'entità my_domain attiva — anche con count 0, così il KPI viene riportato a
    0 quando l'esposizione rientra (altrimenti l'ultimo valore critico resterebbe
    "appeso" all'infinito).
    """
    from .models import FindingStatus, OsintFinding

    open_states = [
        FindingStatus.OPEN, FindingStatus.ACKNOWLEDGED, FindingStatus.IN_PROGRESS,
    ]

    # Plant che hanno almeno un'entità my_domain attiva → universo dei plant da
    # riportare (anche con 0 critici aperti).
    plant_ids = set(
        OsintEntity.objects.filter(
            entity_type=EntityType.MY_DOMAIN, is_active=True, deleted_at__isnull=True,
        ).values_list("source_id", flat=True)
    )
    counts: dict[str, int] = {str(pid): 0 for pid in plant_ids}

    qs = (
        OsintFinding.objects.filter(
            entity__entity_type=EntityType.MY_DOMAIN,
            entity__is_active=True,
            severity="critical",
            status__in=open_states,
            deleted_at__isnull=True,
        )
        .values_list("entity__source_id")
        .order_by()
    )
    from django.db.models import Count
    for source_id, n in qs.annotate(n=Count("id")):
        key = str(source_id)
        if key in counts:
            counts[key] += n
        else:
            counts[key] = n
    return counts


def push_osint_kpis(user=None) -> dict:
    """Pubblica il KPI `osint_critical_open_count` per ogni plant nel KPI engine M08.

    Usa `apps.tasks.services.ingest_kpi_from_api` (stessa pipeline degli ingest
    esterni): trova/crea la KPIDefinition, salva lo snapshot settimanale, valuta
    lo status e scrive l'audit. Da qui il valore confluisce nella management
    review (M13) tra gli `operational_kpis`. Ritorna un riepilogo.
    """
    from apps.tasks.services import ingest_kpi_from_api
    from apps.tasks.models import KPIDefinition

    # Assicura che la KPIDefinition abbia soglie: senza, evaluate_kpi_status
    # ritorna sempre 'ok' (warn/crit None) e il KPI non segnalerebbe mai
    # l'esposizione nella management review. Direzione 'below' (valori bassi =
    # buoni): >0 → warning, >2 → critical (0 ok, 1-2 warning, ≥3 critical).
    kpi_def, created = KPIDefinition.objects.get_or_create(
        kpi_code=OSINT_CRITICAL_KPI_CODE,
        defaults={
            "name": "OSINT — finding critici aperti",
            "description": "Numero di finding OSINT critici aperti sulle entità my_domain del plant.",
            "unit": "n°",
            "source": "api",
            "threshold_warning": 0,
            "threshold_critical": 2,
            "threshold_direction": "below",
        },
    )
    # Retrofit difensivo se la def esisteva già senza soglie (es. creata da un
    # push precedente al fix), senza sovrascrivere eventuali tuning dell'admin.
    if not created and kpi_def.threshold_warning is None and kpi_def.threshold_critical is None:
        kpi_def.threshold_warning = 0
        kpi_def.threshold_critical = 2
        kpi_def.threshold_direction = "below"
        kpi_def.save(update_fields=[
            "threshold_warning", "threshold_critical", "threshold_direction", "updated_at",
        ])

    counts = count_open_critical_findings_by_plant()
    pushed = 0
    for plant_id, value in counts.items():
        try:
            ingest_kpi_from_api(
                kpi_code=OSINT_CRITICAL_KPI_CODE,
                plant_id=plant_id,
                value=value,
                source="osint",
                note="Finding OSINT critici aperti (entità my_domain del plant).",
                user=user,
            )
            pushed += 1
        except Exception as exc:  # noqa: BLE001 - best-effort per plant
            logger.warning("OSINT KPI push failed for plant %s: %s", plant_id, exc)
    logger.info("OSINT KPI push: %d plant aggiornati (%s)", pushed, OSINT_CRITICAL_KPI_CODE)
    return {"plants": len(counts), "pushed": pushed}



# ---------------------------------------------------------------------------
# Dashboard: postura esterna e riepilogo settimanale
# ---------------------------------------------------------------------------

OWN_TYPES = (EntityType.MY_DOMAIN, EntityType.ASSET)


def _own_entities():
    return OsintEntity.objects.filter(entity_type__in=OWN_TYPES, is_active=True, deleted_at__isnull=True)


def external_posture(weeks: int = 12) -> dict:
    """Postura esterna dell'organizzazione (domini e asset propri): voto
    attuale, tendenza settimanale, problemi da correggere; per i fornitori
    solo lo stato delle segnalazioni."""
    from collections import defaultdict
    from datetime import timedelta

    from django.utils import timezone

    from .findings import OPEN_STATUSES, SUPPLIER_FOLLOWUP_DAYS
    from .models import FindingStatus, OsintFinding, OsintScan
    from .scoring import grade_for, security_score

    settings = OsintSettings.load()
    own = _own_entities()
    risks = [r for r in own.values_list("last_score_total", flat=True) if r is not None]
    risk_now = round(sum(risks) / len(risks)) if risks else None

    # Tendenza: per ogni settimana, media dell'ultimo scan di ogni entità fino a fine settimana.
    now = timezone.now()
    start = now - timedelta(weeks=weeks)
    scans = (
        OsintScan.objects.filter(entity__in=own, status="completed", scan_date__gte=start - timedelta(weeks=4))
        .order_by("scan_date").values_list("entity_id", "scan_date", "score_total")
    )
    rows = list(scans)
    trend = []
    for w in range(weeks, -1, -1):
        end = now - timedelta(weeks=w)
        latest: dict = {}
        for eid, date, score in rows:
            if date <= end and score is not None:
                latest[eid] = score
        if latest:
            avg = round(sum(latest.values()) / len(latest))
            trend.append({"week_end": end.date().isoformat(), "security": security_score(avg)})

    week_ago = now - timedelta(days=7)
    own_open = OsintFinding.objects.filter(entity__in=own, status__in=OPEN_STATUSES, deleted_at__isnull=True)
    sup_open = OsintFinding.objects.filter(
        entity__entity_type=EntityType.SUPPLIER, entity__is_active=True, severity="critical",
        status__in=OPEN_STATUSES, deleted_at__isnull=True,
    )
    followup = now - timedelta(days=SUPPLIER_FOLLOWUP_DAYS)
    by_sev = defaultdict(int)
    for sev in own_open.values_list("severity", flat=True):
        by_sev[sev] += 1
    return {
        "security": security_score(risk_now),
        "grade": grade_for(risk_now, settings),
        "entities": len(risks),
        "trend": trend,
        "own": {
            "critical": by_sev["critical"], "warning": by_sev["warning"], "info": by_sev["info"],
            "resolved_week": OsintFinding.objects.filter(
                entity__in=own, status=FindingStatus.RESOLVED, resolved_at__gte=week_ago,
            ).count(),
        },
        "suppliers": {
            "to_report": sup_open.exclude(status=FindingStatus.REPORTED).count(),
            "reported_open": sup_open.filter(status=FindingStatus.REPORTED).count(),
            "overdue": sup_open.filter(status=FindingStatus.REPORTED, reported_at__lt=followup).count(),
        },
    }


def weekly_changes(days: int = 7) -> dict:
    """Cosa è cambiato negli ultimi `days` giorni: nuovi problemi e risolti
    (propri), nuovi critici dei fornitori, variazioni di voto, sottodomini
    da classificare."""
    from datetime import timedelta

    from django.utils import timezone

    from .models import FindingStatus, OsintFinding, OsintSubdomain
    from .scoring import grade_for, security_score

    settings = OsintSettings.load()
    since = timezone.now() - timedelta(days=days)
    own = _own_entities()
    base = OsintFinding.objects.filter(deleted_at__isnull=True).select_related("entity")

    def brief(f):
        return {"id": str(f.pk), "code": f.code, "severity": f.severity, "entity": str(f.entity_id),
                "entity_name": f.entity.display_name, "domain": f.entity.domain}

    new_own = base.filter(entity__in=own, first_seen__gte=since).order_by("-first_seen")
    resolved_own = base.filter(entity__in=own, status=FindingStatus.RESOLVED, resolved_at__gte=since)
    new_sup = base.filter(entity__entity_type=EntityType.SUPPLIER, entity__is_active=True,
                          severity="critical", first_seen__gte=since)
    moved = []
    for e in OsintEntity.objects.filter(is_active=True, deleted_at__isnull=True, last_scan_at__gte=since,
                                        last_score_total__isnull=False, prev_score_total__isnull=False):
        delta = e.prev_score_total - e.last_score_total  # positivo = più sicuro
        if abs(delta) >= 10:
            moved.append({"entity": str(e.pk), "name": e.display_name, "entity_type": e.entity_type,
                          "security": security_score(e.last_score_total),
                          "grade": grade_for(e.last_score_total, settings), "delta": delta})
    moved.sort(key=lambda m: m["delta"])
    return {
        "days": days,
        "new_own": {"count": new_own.count(), "items": [brief(f) for f in new_own[:8]]},
        "resolved_own": resolved_own.count(),
        "new_supplier_critical": {"count": new_sup.count(), "items": [brief(f) for f in new_sup[:8]]},
        "score_changes": moved[:10],
        "pending_subdomains": OsintSubdomain.objects.filter(status="pending", deleted_at__isnull=True).count(),
    }


def supplier_posture(supplier_id) -> list[dict]:
    """Postura esterna dei domini di un fornitore (per la scheda M14): voto,
    critici aperti e storico delle segnalazioni."""
    from .findings import OPEN_STATUSES, report_overdue
    from .models import OsintFinding
    from .scoring import grade_for, security_score

    settings = OsintSettings.load()
    result = []
    for e in OsintEntity.objects.filter(entity_type=EntityType.SUPPLIER, source_id=supplier_id,
                                        is_active=True, deleted_at__isnull=True):
        findings = OsintFinding.objects.filter(entity=e, deleted_at__isnull=True)
        critical = findings.filter(severity="critical", status__in=OPEN_STATUSES)
        reports = findings.filter(reported_at__isnull=False).select_related("reported_by").order_by("-reported_at")
        result.append({
            "entity": str(e.pk), "domain": e.domain, "name": e.display_name,
            "deep_monitoring": e.deep_monitoring, "service_hosts": e.service_hosts,
            "security": security_score(e.last_score_total), "grade": grade_for(e.last_score_total, settings),
            "last_scan_at": e.last_scan_at,
            "critical_open": [{"id": str(f.pk), "code": f.code, "status": f.status,
                               "first_seen": f.first_seen, "reported_at": f.reported_at,
                               "overdue": report_overdue(f)} for f in critical],
            "reports": [{"id": str(f.pk), "code": f.code, "status": f.status, "reported_at": f.reported_at,
                         "resolved_at": f.resolved_at, "note": f.report_note} for f in reports[:20]],
        })
    return result
