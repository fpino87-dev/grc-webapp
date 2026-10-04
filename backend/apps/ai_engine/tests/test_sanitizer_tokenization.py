"""Tokenizzazione reversibile, guardia in uscita e minimizzazione dei prompt IA.

Batteria multilingua: ciò che identifica persone, siti, sistemi e controparti
non deve arrivare al provider cloud; testo normativo, codici dei controlli,
date, durate e importi devono restare intatti (il modello deve capire).
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.ai_engine.router import LlmUnavailable, route
from apps.ai_engine.sanitizer import EgressGuard, Sanitizer


@pytest.fixture
def org(db):
    from apps.assets.models import AssetIT
    from apps.plants.models import BusinessUnit, Plant
    from apps.suppliers.models import Supplier

    bu = BusinessUnit.objects.create(code="BU-TK", name="Divisione Freni")
    plant = Plant.objects.create(
        code="TK-01", name="Stabilimento Nord", country="IT", bu=bu,
        nis2_scope="essenziale", status="attivo", domain="acme-nord.example",
    )
    other = Plant.objects.create(
        code="TK-02", name="Stabilimento Sud", country="PL",
        nis2_scope="essenziale", status="attivo",
    )
    get_user_model().objects.create_user(
        username="gverdi", email="g.verdi@acme-nord.example", password="x",
        first_name="Giacinto", last_name="Verdolini",
    )
    AssetIT.objects.create(
        plant=plant, name="Gestionale Paghe", asset_type="IT", criticality=4,
        fqdn="paghe01.acme-nord.example", ip_address="10.1.2.3",
    )
    Supplier.objects.create(name="Logistica Brambilla", vat_number="IT01234567897",
                            email="info@brambilla.example")
    return {"plant": plant, "other": other}


LEAKS = [
    ("utente registrato", "Giacinto Verdolini ha aperto il ticket", "Verdolini"),
    ("utente invertito", "Verdolini Giacinto ha aperto", "Verdolini"),
    ("utente con iniziale", "G. Verdolini ha aperto", "Verdolini"),
    ("username", "creato da gverdi ieri", "gverdi"),
    ("persona non registrata", "Mario Bianchi ha segnalato il problema", "Bianchi"),
    ("persona dopo articolo", "Il Mario Bianchi ha segnalato", "Bianchi"),
    ("cognome nome PL", "Kowalska Anna ha confermato", "Kowalska"),
    ("titolo IT", "contattare la dott.ssa Neri", "Neri"),
    ("titolo PL", "rozmowa z Pan Nowak", "Nowak"),
    ("titolo TR", "Ahmet Bey ha risposto", "Ahmet"),
    ("email", "scrivere a mario.bianchi@example.com", "mario.bianchi"),
    ("email mascherata", "owner ma***@brambilla.example", "brambilla.example"),
    ("tel IT spaziato", "chiamare +39 02 1234 5678", "1234 5678"),
    ("tel IT mobile", "cell 333 1234567", "1234567"),
    ("tel PL", "tel +48 123 456 789", "456 789"),
    ("tel TR", "tel +90 212 555 12 34", "555 12 34"),
    ("tel FR", "tel +33 1 23 45 67 89", "45 67 89"),
    ("codice fiscale", "CF rssmra80a01h501u", "rssmra80a01h501u"),
    ("P.IVA", "P.IVA 12345678901", "12345678901"),
    ("P.IVA con prefisso", "VAT IT12345678901", "12345678901"),
    ("NIP", "NIP 123-456-32-18", "123-456-32-18"),
    ("PESEL", "PESEL 44051401359", "44051401359"),
    ("IPv4", "host 192.168.10.20", "192.168.10.20"),
    ("IPv6", "addr fe80::1ff:fe23:4567:890a", "fe80::1ff"),
    ("IBAN", "IBAN IT60X0542811101000000123456", "0542811101"),
    ("IBAN spaziato", "IBAN IT60 X054 2811 1010 0000 0123 456", "2811 1010"),
    ("indirizzo IT", "sede in Via Garibaldi 12, 20100 Milano", "Garibaldi"),
    ("indirizzo PL", "ul. Długa 5, 00-950 Warszawa", "Długa"),
    ("dominio interno", "server srv-dc01.corp.local", "srv-dc01"),
    ("hostname maiuscolo", "copia su FILESRV02", "FILESRV02"),
    ("URL", "vedi https://intranet.example/hr", "intranet.example"),
    ("percorso UNC", r"cartella \\fileserver\share\hr", "fileserver"),
    ("sito", "problema a Stabilimento Nord (TK-01)", "Stabilimento Nord"),
    ("sito fuori perimetro", "anche Stabilimento Sud è coinvolto", "Stabilimento Sud"),
    ("BU", "la Divisione Freni ha chiesto", "Divisione Freni"),
    ("asset", "fermo del Gestionale Paghe", "Gestionale Paghe"),
    ("FQDN asset", "raggiungibile su paghe01.acme-nord.example", "paghe01"),
    ("dominio del sito", "mail da vpn.acme-nord.example", "acme-nord"),
    ("fornitore", "ritardo di Logistica Brambilla", "Brambilla"),
]

UNCHANGED = [
    "A.8.23 ISA-4.1.2-VH ACN-NIS2-PR.PS-03 TISAX-L3-PHYSEC-5.3 OT_MAL LO_FRA",
    "ISO 27001:2022, ISO/IEC 27002, IEC 62443, Regolamento (UE) 2016/679, NIS2 art. 23, CVE-2024-3094",
    "AES256, SHA256, RSA2048, TLS 1.3, MS Teams, Arch Linux, Microsoft 365",
    "notifica entro 24 ore, report entro 72 ore, inviato via PEC entro 72 ore, al 95% dei casi",
    "il 15/01/2026 alle 10:30, poi 2026-10-04 e 04.10.2026",
    "impatto 50000 Euro, soglia 1.000.000 EUR",
    "codici 79211100-0 e 72000000-5",
    "Business Continuity Plan, Risk Owner, Data Protection Officer",
    "Il Firewall perimetrale e il Server di backup sono ridondati",
]


@pytest.mark.django_db
@pytest.mark.parametrize("label,text,secret", LEAKS, ids=[c[0] for c in LEAKS])
def test_identifying_data_is_tokenized(org, label, text, secret):
    out = Sanitizer().tokenize(text)
    assert secret.lower() not in out.lower(), f"{label}: {out}"
    assert "[" in out


@pytest.mark.django_db
@pytest.mark.parametrize("text", UNCHANGED)
def test_normative_and_operational_text_is_untouched(org, text):
    assert Sanitizer().tokenize(text) == text


@pytest.mark.django_db
def test_tokens_are_typed_stable_and_reversible(org):
    s = Sanitizer()
    prompt = s.tokenize("Giacinto Verdolini (g.verdi@acme-nord.example) e poi di nuovo Verdolini Giacinto")
    system = s.tokenize("Rispondi a Giacinto Verdolini")
    # Stesso soggetto, varianti diverse → stesso token, anche fra prompt e system
    assert prompt.count("[PERSON_1]") == 2 and "[EMAIL_1]" in prompt
    assert system == "Rispondi a [PERSON_1]"
    restored = s.desanitize("Contattare [person_1] a [EMAIL_1]", s.token_map)
    assert restored == "Contattare Giacinto Verdolini a g.verdi@acme-nord.example"


@pytest.mark.django_db
def test_existing_tokens_are_not_retokenized(org):
    s = Sanitizer()
    once = s.tokenize("Mario Bianchi a Stabilimento Nord, [PERSONA_1]")
    assert s.tokenize(once) == once


@pytest.mark.django_db
def test_guard_blocks_residual_identifiers_and_reports_only_counts(org):
    s = Sanitizer()
    result = EgressGuard(s).check("testo con x@y.example e 10.0.0.1 e Stabilimento Nord")
    assert result.blocked is True
    assert result.findings == {"EMAIL": 1, "IP": 1, "ENTITY": 1}
    assert EgressGuard(s).check(s.tokenize("x@y.example, 10.0.0.1, Stabilimento Nord")).blocked is False


@pytest.fixture
def cloud_config(db):
    from apps.ai_engine.models import AiProviderConfig
    return AiProviderConfig.objects.create(
        name="tk", active=True, cloud_provider="anthropic", cloud_model="m",
        api_key="sk-test", monthly_token_budget=100000, task_routing={"unit_test": "cloud"},
    )


@pytest.mark.django_db
def test_router_sends_only_tokens_and_restores_answer(org, cloud_config):
    captured = {}

    def fake_cloud(config, prompt, system, max_tokens, model=""):
        captured.update(prompt=prompt, system=system)
        return "Coinvolgere [PERSON_1] per [SITE_1].", 10

    with patch("apps.ai_engine.router._call_cloud", side_effect=fake_cloud), \
         patch("apps.ai_engine.router.resolve_cloud_model", return_value=("m", None)):
        result = route("unit_test", "Giacinto Verdolini segnala un guasto a Stabilimento Nord",
                       system="Assisti Giacinto Verdolini")

    assert "Verdolini" not in captured["prompt"] + captured["system"]
    assert "Stabilimento Nord" not in captured["prompt"]
    assert captured["system"] == "Assisti [PERSON_1]"
    assert result["text"] == "Coinvolgere Giacinto Verdolini per Stabilimento Nord."
    assert result["privacy"]["guard"]["blocked"] is False


@pytest.mark.django_db
def test_router_fails_closed_when_guard_finds_residuals(org, cloud_config):
    """Se la tokenizzazione lascia passare qualcosa, il cloud non riceve nulla."""
    with patch.object(Sanitizer, "tokenize", lambda self, text: text), \
         patch("apps.ai_engine.router._call_cloud") as cloud, \
         patch("apps.ai_engine.router._call_ollama", return_value="locale") as ollama:
        result = route("unit_test", "scrivere a mario@example.com")

    cloud.assert_not_called()
    ollama.assert_called_once()
    assert result["provider"] == "ollama" and result["used_fallback"] is True
    assert result["privacy"]["guard"] == {"blocked": True, "findings": {"EMAIL": 1}}


@pytest.mark.django_db
def test_router_raises_when_guard_blocks_and_fallback_disabled(org, cloud_config):
    cloud_config.fallback_mode = "disabled"
    cloud_config.save(update_fields=["fallback_mode"])
    with patch.object(Sanitizer, "tokenize", lambda self, text: text), \
         patch("apps.ai_engine.router._call_cloud") as cloud, \
         patch("apps.ai_engine.router._call_ollama") as ollama:
        with pytest.raises(LlmUnavailable):
            route("unit_test", "scrivere a mario@example.com")
    cloud.assert_not_called()
    ollama.assert_not_called()


# ── Minimizzazione ─────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_gap_actions_prompt_has_no_site_name(org):
    from apps.ai_engine import tasks_ai
    from apps.controls.models import Control, ControlInstance, Framework

    from django.utils import timezone

    fw = Framework.objects.create(code="TKFW", name="FW", version="1", published_at=timezone.now())
    control = Control.objects.create(framework=fw, external_id="TK.1", translations={"it": {"title": "Ctrl"}})
    ci = ControlInstance.objects.create(plant=org["plant"], control=control, status="gap")
    with patch.object(tasks_ai, "route", return_value={"text": "{}"}) as fake:
        tasks_ai.suggest_gap_actions(ci, user=None)
    assert "Stabilimento Nord" not in fake.call_args.kwargs["prompt"]
    assert "SITO" not in fake.call_args.kwargs["prompt"]


@pytest.mark.django_db
def test_rca_prompt_uses_asset_type_not_name(org):
    from apps.ai_engine import tasks_ai
    from apps.assets.models import Asset
    from apps.incidents.models import Incident

    from django.utils import timezone

    incident = Incident.objects.create(
        plant=org["plant"], title="Guasto", description="Fermo", severity="media", detected_at=timezone.now(),
    )
    incident.assets.add(Asset.objects.get(name="Gestionale Paghe"))
    with patch.object(tasks_ai, "route", return_value={"text": "{}"}) as fake:
        tasks_ai.draft_rca(incident, user=None)
    prompt = fake.call_args.kwargs["prompt"]
    assert "Gestionale Paghe" not in prompt
    assert "IT (criticità 4/5)" in prompt


@pytest.mark.django_db
def test_assistant_document_tool_exposes_no_owner_email(org):
    from datetime import date

    from apps.ai_engine.agent_tools import get_expired_documents
    from apps.documents.models import Document

    owner = get_user_model().objects.get(username="gverdi")
    Document.objects.create(title="Policy", plant=org["plant"], owner=owner, expiry_date=date(2020, 1, 1))
    admin = get_user_model().objects.create_superuser("root-tk", "root@tk.example", "x")
    docs = get_expired_documents(admin, org["plant"].pk)
    assert docs and docs[0]["has_owner"] is True
    assert "acme-nord" not in str(docs)
