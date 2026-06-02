"""Test del de-dup scan per dominio (#2).

Verifica:
- run_weekly_scan raggruppa le entità con lo stesso dominio in un unico
  run_domain_scan e dispatcha le altre come run_entity_scan;
- run_domain_scan sceglie come primaria una my_domain (HIBP/dnstwist-only);
- _propagate_scan copia i campi domain-level ma RICALCOLA lo score per entità,
  propaga i sottodomini e azzera lookalike/HIBP per le entità non-my_domain.

Nessuna chiamata di rete: l'enrichment è mockato o si costruisce lo scan donor
a mano.
"""
from unittest.mock import MagicMock, patch

import pytest


def _plant(code):
    from apps.plants.models import Plant
    return Plant.objects.create(code=code, name=code, country="IT", nis2_scope="non_soggetto", status="attivo")


def _entity(plant, domain, **kw):
    from apps.osint.models import OsintEntity, EntityType, SourceModule
    defaults = dict(
        entity_type=EntityType.MY_DOMAIN,
        source_module=SourceModule.SITES,
        source_id=plant.id,
        domain=domain,
        display_name=domain,
        scan_frequency="weekly",
        is_active=True,
    )
    defaults.update(kw)
    return OsintEntity.objects.create(**defaults)


# ── grouping nel weekly scan ────────────────────────────────────────────────

@pytest.mark.django_db
def test_weekly_scan_groups_entities_sharing_domain():
    from apps.osint import tasks

    p1, p2, p3 = _plant("DD1"), _plant("DD2"), _plant("DD3")
    _entity(p1, "shared.example.com")
    _entity(p2, "shared.example.com")          # stesso dominio di p1 → gruppo
    _entity(p3, "unique.example.com")           # dominio unico → entity scan

    with patch("apps.osint.services.aggregate_entities"), \
         patch("apps.osint.tasks.run_domain_scan.delay") as mock_domain, \
         patch("apps.osint.tasks.run_entity_scan.delay") as mock_entity:
        result = tasks.run_weekly_scan()

    # Un solo dominio dedup-ato (shared con 2 entità)
    assert result["deduped_domains"] == 1
    assert result["dispatched"] == 3  # 2 nel gruppo + 1 singola
    # run_domain_scan chiamato una volta con il dominio condiviso e 2 id
    assert mock_domain.call_count == 1
    domain_arg, ids_arg = mock_domain.call_args.args
    assert domain_arg == "shared.example.com"
    assert len(ids_arg) == 2
    # run_entity_scan chiamato solo per il dominio unico
    assert mock_entity.call_count == 1


# ── run_domain_scan: primaria my_domain + propagazione ──────────────────────

@pytest.mark.django_db
def test_run_domain_scan_prefers_my_domain_primary():
    from apps.osint import tasks
    from apps.osint.models import EntityType, SourceModule

    p1, p2 = _plant("DP1"), _plant("DP2")
    # Ordine: prima il fornitore, poi il my_domain → la primaria deve essere il my_domain
    supplier = _entity(
        p1, "mix.example.com",
        entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
    )
    mydomain = _entity(p2, "mix.example.com")

    fake_scan = MagicMock(status="completed", score_total=10, pk="s1", entity_id=mydomain.pk)
    with patch("apps.osint.enrichers.run.run_enrichment", return_value=fake_scan) as mock_run, \
         patch("apps.osint.enrichers.run._propagate_scan") as mock_prop:
        result = tasks.run_domain_scan("mix.example.com", [str(supplier.pk), str(mydomain.pk)])

    # run_enrichment chiamato sulla my_domain (primaria), non sul fornitore
    assert mock_run.call_args.args[0].pk == mydomain.pk
    # propagazione sull'altra entità (il fornitore)
    assert mock_prop.call_count == 1
    assert mock_prop.call_args.args[0].pk == supplier.pk
    assert result["propagated"] == 1


@pytest.mark.django_db
def test_run_domain_scan_no_active_entities():
    from apps.osint import tasks
    result = tasks.run_domain_scan("ghost.example.com", ["00000000-0000-0000-0000-0000000000ff"])
    assert result["error"] == "no_entities"


# ── _propagate_scan: copia domain-level, ricalcolo score, sottodomini ───────

@pytest.mark.django_db
def test_propagate_copies_fields_but_recomputes_score():
    from apps.osint.models import OsintScan, OsintSettings, OsintSubdomain, SubdomainStatus
    from apps.osint.enrichers.run import _propagate_scan

    p_primary, p_secondary = _plant("PR1"), _plant("PR2")
    primary = _entity(p_primary, "grp.example.com")
    secondary = _entity(p_secondary, "grp.example.com")

    # Scan donor con campi domain-level valorizzati e score "sporchi" (99) che
    # NON devono essere copiati: lo score va ricalcolato per l'entità.
    source = OsintScan.objects.create(
        entity=primary, status="completed",
        ssl_valid=True, ssl_days_remaining=100, ssl_issuer="Let's Encrypt",
        mx_present=False, dmarc_present=None,
        in_blacklist=False, blacklist_sources=[],
        security_headers={"missing": []},
        domain_registrar="GANDI",
        score_ssl=99, score_dns=99, score_reputation=99, score_grc_context=99, score_total=99,
    )
    OsintSubdomain.objects.create(entity=primary, subdomain="api.grp.example.com", status=SubdomainStatus.INCLUDED)

    scan = _propagate_scan(secondary, source, OsintSettings.load())

    # Campi domain-level copiati
    assert scan.ssl_days_remaining == 100
    assert scan.ssl_issuer == "Let's Encrypt"
    assert scan.domain_registrar == "GANDI"
    # Score RICALCOLATO (fields benigni → 0), non il 99 copiato
    assert scan.score_total == 0
    assert scan.score_total != source.score_total
    # Sottodominio propagato alla secondaria (copia DB→DB)
    assert OsintSubdomain.objects.filter(entity=secondary, subdomain="api.grp.example.com").exists()
    # status ereditato
    assert scan.status == "completed"


@pytest.mark.django_db
def test_propagate_zeroes_lookalike_and_hibp_for_non_my_domain():
    from apps.osint.models import (
        OsintScan, OsintSettings, EntityType, SourceModule, FindingCode, OsintFinding,
    )
    from apps.osint.enrichers.run import _propagate_scan

    p1, p2 = _plant("LA1"), _plant("LA2")
    primary = _entity(p1, "brand.example.com")  # my_domain
    supplier = _entity(
        p2, "brand.example.com",
        entity_type=EntityType.SUPPLIER, source_module=SourceModule.SUPPLIERS,
    )

    source = OsintScan.objects.create(
        entity=primary, status="completed",
        ssl_valid=True, ssl_days_remaining=200, mx_present=False,
        lookalike_domains=[{"domain": "brand-login.com", "ips": ["1.2.3.4"], "mx": True}],
        hibp_breaches=3, hibp_data_types=["Passwords"],
    )

    scan = _propagate_scan(supplier, source, OsintSettings.load())

    # lookalike/HIBP azzerati per il fornitore → nessun finding lookalike/breach
    assert scan.lookalike_domains == []
    assert scan.hibp_breaches is None
    assert not OsintFinding.objects.filter(entity=supplier, code=FindingCode.LOOKALIKE).exists()
    assert not OsintFinding.objects.filter(entity=supplier, code=FindingCode.BREACH).exists()


@pytest.mark.django_db
def test_propagate_grc_differs_between_plants():
    """Due plant con stesso dominio ma gap controlli diversi → score GRC diverso."""
    import datetime
    from apps.controls.models import ControlInstance, Control, Framework
    from apps.osint.models import OsintScan, OsintSettings
    from apps.osint.enrichers.run import _propagate_scan

    p_clean, p_gappy = _plant("GR1"), _plant("GR2")
    fw = Framework.objects.create(code="ISO27001", name="ISO", version="1", published_at=datetime.date(2024, 1, 1))
    ctrl = Control.objects.create(framework=fw, external_id="A.5.1", translations={"title": {"it": "x"}})
    # Un gap sul plant "gappy" → +20 GRC (>=1)
    ControlInstance.objects.create(plant=p_gappy, control=ctrl, status="gap")

    primary = _entity(p_clean, "g.example.com")
    gappy = _entity(p_gappy, "g.example.com")

    source = OsintScan.objects.create(
        entity=primary, status="completed",
        ssl_valid=True, ssl_days_remaining=300, mx_present=False, in_blacklist=False,
    )
    scan = _propagate_scan(gappy, source, OsintSettings.load())
    # GRC pesato 20% su my_domain: >=1 gap → grc 20 → total >= 20*0.20 = 4
    assert scan.score_grc_context >= 20
    assert scan.score_total >= 4
