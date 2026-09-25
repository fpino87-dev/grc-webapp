"""Score Engine OSINT — Step 4.

Calcola i 4 score dimensionali e lo score aggregato pesato.
Range 0-100 (0 = ottimo, 100 = critico).

Pesi:
  my_domain:  SSL 25% | DNS 25% | Rep 30% | GRC 20%
  altri:      SSL 30% | DNS 30% | Rep 40% | (GRC non applicabile)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.osint.models import OsintEntity, OsintScan

logger = logging.getLogger(__name__)


def _score_ssl(scan: "OsintScan", warning_days: int = 60, entity=None) -> int:
    from apps.osint.posture import expects_web

    if entity is not None and not expects_web(entity, scan):
        return 0  # dominio non atteso servire web: nulla da valutare
    if scan.ssl_valid is None:
        # Nessun HTTPS. Due casi opposti, che prima collassavano entrambi in
        # "non applicabile": se il sito risponde in chiaro il traffico è
        # leggibile da chiunque ed è più grave di un certificato in scadenza;
        # se non risponde nulla non c'è niente da proteggere.
        if getattr(scan, "http_only", None) is True:
            # Massimo della dimensione: un certificato scaduto cifra ancora,
            # per quanto non autenticato; nessun HTTPS non cifra affatto.
            return 100
        return 0
    if scan.ssl_valid is False:
        return 100
    days = scan.ssl_days_remaining
    if days is None or days <= 0:
        return 100
    if days <= 14:
        return 90
    if days <= 30:
        return 70
    if days <= warning_days:
        return 40
    if days <= 90:
        return 20
    return 0


def _score_dns(scan: "OsintScan", entity=None) -> int:
    from apps.osint.posture import expects_mail

    base = 0
    # SPF e DMARC si valutano solo con posta accertata: `is True` e non
    # `is not False`, altrimenti un mx_present a None (dominio non sondabile,
    # DNS in errore) verrebbe trattato come "ha la posta" e penalizzato.
    mail_expected = (
        expects_mail(entity, scan) if entity is not None else scan.mx_present is True
    )
    if mail_expected:
        if scan.spf_present is False:
            base += 40
        elif scan.spf_policy == "+all":
            base += 20
        if scan.dmarc_present is False:
            base += 30
        elif scan.dmarc_policy == "none":
            base += 15
        # Posture DKIM/MTA-STS (penalità minori). Guardia `is False`: i campi
        # restano None se non sondati (dominio senza mail o scan vecchio) → nessuna
        # penalità, nessuna regressione sugli score esistenti.
        if getattr(scan, "dkim_present", None) is False:
            base += 15
        if getattr(scan, "mta_sts_present", None) is False:
            base += 10
    return min(base, 100)


def _score_reputation(scan: "OsintScan") -> int:
    base = 0
    gsb = scan.gsb_status or ""
    if gsb and gsb != "safe":
        return 100  # esce subito

    if scan.in_blacklist:
        base += 60

    vt = scan.vt_malicious or 0
    if vt > 5:
        base += 40
    elif vt > 0:
        base += 20

    abuse = scan.abuseipdb_score or 0
    if abuse > 50:
        base += 30
    elif abuse > 20:
        base += 15

    pulses = scan.otx_pulses or 0
    if pulses > 5:
        base += 20
    elif pulses > 0:
        base += 10

    # abuse.ch CTI: segnali forti di compromissione attiva. Guardia `or 0` così i
    # campi None (enricher no-op senza chiave / scan vecchi) non penalizzano.
    if (getattr(scan, "threatfox_iocs", None) or 0) > 0:
        base += 50  # IoC malware/botnet attivo associato al dominio o al suo IP
    if (getattr(scan, "urlhaus_urls", None) or 0) > 0:
        base += 40  # l'host distribuisce/ha distribuito malware

    return min(base, 100)


def _has_active_compromise(scan: "OsintScan") -> bool:
    """
    Il dominio mostra segni di compromissione ATTIVA?

    Non «è configurato male», ma «qualcuno lo sta usando per fare del male
    adesso»: segnalato da Google Safe Browsing, in blacklist, associato a IoC
    malware o a URL che distribuiscono malware. Sono condizioni che cambiano la
    natura del giudizio, non il suo grado.
    """
    gsb = (getattr(scan, "gsb_status", "") or "").strip()
    return bool(
        (gsb and gsb != "safe")
        or getattr(scan, "in_blacklist", False)
        or (getattr(scan, "threatfox_iocs", None) or 0) > 0
        or (getattr(scan, "urlhaus_urls", None) or 0) > 0
    )


def _score_grc(entity: "OsintEntity", scan: "OsintScan") -> int:
    """Applicabile solo a entity_type='my_domain'."""
    from apps.osint.models import EntityType
    if entity.entity_type != EntityType.MY_DOMAIN:
        return 0

    base = 0
    # `is_nis2_critical` NON entra più nel punteggio: essere critici NIS2 è un
    # attributo di perimetro — quanto conta questo sito — non una debolezza.
    # Sommarlo significava penalizzare un dominio perché è importante, cioè
    # confondere l'impatto con la vulnerabilità.

    # Rischi aperti (non archiviati e non accettati formalmente) sul plant
    # sorgente. RiskAssessment ha una FK diretta a plant; gli stati validi sono
    # bozza/completato/archiviato (vedi apps.risk.models.RiskAssessment).
    try:
        from apps.risk.models import RiskAssessment
        open_risks = RiskAssessment.objects.filter(
            plant_id=entity.source_id,
            status__in=["bozza", "completato"],
            risk_accepted=False,
            deleted_at__isnull=True,
        ).count()
        if open_risks >= 3:
            base += 40
        elif open_risks >= 1:
            base += 20
    except Exception as exc:  # pragma: no cover - difensivo su schema drift
        logger.debug("score_grc: open_risks query failed for %s: %s", entity.domain, exc)

    # Gap controlli collegati al plant. Gli stati ControlInstance sono
    # compliant/parziale/gap/na/non_valutato: il gap vero è "gap" (+ "parziale").
    try:
        from apps.controls.models import ControlInstance
        gap_controls = ControlInstance.objects.filter(
            plant_id=entity.source_id,
            status__in=["gap", "parziale"],
            deleted_at__isnull=True,
        ).count()
        if gap_controls >= 5:
            base += 40
        elif gap_controls >= 1:
            base += 20
    except Exception as exc:  # pragma: no cover - difensivo su schema drift
        logger.debug("score_grc: gap_controls query failed for %s: %s", entity.domain, exc)

    return min(base, 100)


def compute_scores(entity: "OsintEntity", scan: "OsintScan", settings=None) -> None:
    """Calcola e scrive i 4 score + score_total nel scan (non salva — il chiamante salva).

    `settings` opzionale: se il chiamante lo possiede già evita una query in più.
    """
    from apps.osint.models import OsintSettings

    if settings is None:
        settings = OsintSettings.load()
    if getattr(entity, "entity_type", None) == "supplier":
        return _compute_supplier_scores(entity, scan, settings)
    ssl = _score_ssl(scan, warning_days=settings.ssl_expiry_warning_days, entity=entity)
    dns = _score_dns(scan, entity=entity)
    rep = _score_reputation(scan)
    grc = _score_grc(entity, scan)

    scan.score_ssl = ssl
    scan.score_dns = dns
    scan.score_reputation = rep
    scan.score_grc_context = grc

    # Lo score misura l'ESPOSIZIONE: SSL, DNS, reputazione. La dimensione GRC
    # (rischi aperti e controlli in gap del sito dietro il dominio) resta
    # calcolata e consultabile in `score_grc_context`, ma non entra più nel
    # totale: quanto sei attaccabile dall'esterno e quanto sei messo male in
    # compliance sono due assi diversi, e sommarli produce un numero che non
    # risponde a nessuna delle due domande. `weight_grc` resta nelle
    # impostazioni per non rompere configurazioni esistenti, ma non è più usato
    # nel calcolo del totale.
    pairs = [
        (ssl, settings.weight_ssl),
        (dns, settings.weight_dns),
        (rep, settings.weight_reputation),
    ]
    total_w = sum(w for _, w in pairs) or 1
    total = sum(v * w for v, w in pairs) / total_w

    # Pavimento sulla compromissione in atto. Una media pesata, per costruzione,
    # diluisce: con i pesi di default un dominio che distribuisce malware ma ha
    # certificato e DNS in ordine finiva a 27 su 100, cioè "ok". Un segnale di
    # compromissione non va mediato con la scadenza di un certificato: deve
    # dominare, e porta il totale almeno alla soglia critica.
    if _has_active_compromise(scan):
        total = max(total, settings.score_threshold_critical)

    scan.score_total = round(total)


def _compute_supplier_scores(entity, scan, settings) -> None:
    """Fornitori: rischio per pilastri — compromissione, impersonificazione,
    esposizione (solo monitoraggio approfondito) e maturità, che pesa poco.
    La compromissione in atto domina il totale."""
    from datetime import date

    ssl = _score_ssl(scan, warning_days=settings.ssl_expiry_warning_days, entity=entity)
    dns = _score_dns(scan, entity=entity)
    rep = _score_reputation(scan)
    scan.score_ssl, scan.score_dns, scan.score_reputation = ssl, dns, rep
    scan.score_grc_context = 0

    def months(d):
        try:
            return (date.today() - date.fromisoformat(str(d)[:10])).days / 30.4
        except ValueError:
            return 999

    compromise = 100 if (_has_active_compromise(scan) or scan.ransomware_hits) else 0
    breaches = scan.hibp_domain_breaches or []
    if not compromise and any(months(b.get("date")) <= 12 for b in breaches):
        compromise = 60
    elif not compromise and any(months(b.get("date")) <= 24 for b in breaches):
        compromise = 20

    imp = 0
    if scan.dmarc_present is False:
        imp += 60
    elif scan.dmarc_present is True and scan.dmarc_policy == "none":
        imp += 40
    # solo sosia registrati di recente: gli omonimi storici non sono impostori
    looks = [x for x in (scan.lookalike_domains or []) if x.get("recent")]
    imp += 40 if any(x.get("mx") for x in looks) else (15 if looks else 0)
    if scan.domain_expiry_date:
        days = (scan.domain_expiry_date - date.today()).days
        imp += 100 if days <= 0 else (30 if days <= 30 else 0)
    imp = min(imp, 100)

    exposure = None
    certs = [c for c in (scan.service_checks or []) if c.get("reachable") and c.get("days_remaining") is not None]
    cert_risk = 40 if any(c["days_remaining"] <= 0 for c in certs) else (15 if any(c["days_remaining"] <= 14 for c in certs) else 0)
    if entity.deep_monitoring:
        remote = scan.remote_access or []
        exposure = 100 if any(r.get("kev") for r in remote) else (50 if any(r.get("admin_ports") for r in remote) else 0)
        exposure = min(100, exposure + cert_risk + (40 if scan.takeover_candidates else 0))
    elif certs:
        exposure = cert_risk

    maturity = round((ssl + dns) / 2)
    if exposure is None:
        blended = 0.7 * imp + 0.3 * maturity
    else:
        blended = 0.45 * imp + 0.35 * exposure + 0.20 * maturity
    scan.score_compromise, scan.score_impersonation = compromise, imp
    scan.score_exposure, scan.score_maturity = exposure, maturity
    scan.score_total = round(max(compromise, blended))


def score_delta(entity: "OsintEntity", current_scan: "OsintScan") -> int:
    """Delta rispetto al penultimo scan. Positivo = peggiorato, negativo = migliorato."""
    from apps.osint.models import OsintScan
    prev = (
        OsintScan.objects.filter(entity=entity, status="completed")
        .exclude(pk=current_scan.pk)
        .order_by("-scan_date")
        .first()
    )
    if prev is None:
        return 0
    return current_scan.score_total - prev.score_total


def classify_score(score: int, settings=None) -> str:
    """Ritorna 'critical' | 'warning' | 'attention' | 'ok'.

    Le soglie sono configurabili via OsintSettings. Se `settings` non è passato si
    usano i default storici (70/50/30) — così le chiamate pure e i test restano
    invariati senza toccare il DB."""
    crit, warn, att = 70, 50, 30
    if settings is not None:
        crit = settings.score_threshold_critical
        warn = settings.score_threshold_warning
        att = getattr(settings, "score_threshold_attention", 30)
    if score >= crit:
        return "critical"
    if score >= warn:
        return "warning"
    if score >= att:
        return "attention"
    return "ok"



def security_score(risk: int | None) -> int | None:
    """Il punteggio interno misura il rischio (0 = bene); in interfaccia si
    mostra la sicurezza, così più alto = meglio ovunque."""
    return None if risk is None else max(0, min(100, 100 - risk))


def grade_for(risk: int | None, settings=None) -> str | None:
    """Voto A–F allineato alle soglie configurate: critico = F, warning = D,
    attenzione = C, ok = B (A se la sicurezza è almeno 90)."""
    if risk is None:
        return None
    cls = classify_score(risk, settings)
    if cls == "critical":
        return "F"
    if cls == "warning":
        return "D"
    if cls == "attention":
        return "C"
    return "A" if security_score(risk) >= 90 else "B"
