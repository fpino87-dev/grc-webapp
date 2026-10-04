"""Tokenizzazione reversibile dei dati identificativi prima dell'invio all'IA.

Ogni dato che identifica persone, siti, sistemi o controparti viene sostituito
da un token tipizzato e stabile nella richiesta (`[PERSON_1]`, `[HOST_2]`,
`[EMAIL_1]`...). Il modello ragiona sui token; la tabella token → valore resta
sul server, in memoria, solo per la durata della richiesta, e serve a
ripristinare i valori veri nella risposta (`desanitize`). Non viene mai
salvata né scritta nei log.

Fonti, in ordine di applicazione:
1. regole sui formati: email, URL, IPv4/IPv6, IBAN, partite IVA con prefisso,
   codice fiscale, telefoni di tutti i paesi (`phonenumbers`);
2. dizionario dal database, sempre su TUTTA l'organizzazione: utenti, siti,
   BU, asset, fornitori, domini monitorati, persone citate a testo libero;
3. euristiche: domini interni, hostname, indirizzi, persone con titolo o con
   un nome proprio comune, numeri lunghi (NIP, PESEL, TCKN, SIRET, conti).

È pseudonimizzazione, non anonimato: il testo libero può ancora contenere
elementi non riconosciuti. Per questo, prima di ogni invio al cloud,
`EgressGuard` ricontrolla il testo e, se resta qualcosa, il router non usa il
cloud (fail-closed).
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

import phonenumbers

from .privacy_lexicon import (
    CURRENCY_WORDS,
    FIRST_NAMES,
    GENERIC_NAMES,
    NOT_SURNAMES,
    STANDARD_PREFIXES,
    TITLES_AFTER,
    TITLES_BEFORE,
)

# Un token già inserito (nostro o di altri pseudonimizzatori, es. [PERSONA_1]):
# le regole lavorano solo sul testo fuori dai token.
TOKEN_RE = re.compile(r"\[[A-Z]+(?:_[A-Z0-9]+)*\]")

_UP = "A-ZÀ-ÖØ-ÞĄĆĘŁŃÓŚŹŻÇĞİÖŞÜ"
_LO = "a-zß-öø-ÿąćęłńóśźżçğıöşü"
_NAME_WORD = rf"[{_UP}][{_LO}'’\-]+"

EMAIL_RE = re.compile(r"[\w.%+*\-]+@[\w\-]+(?:\.[\w\-]+)*\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b(?:https?|ftp|smb|file|ldaps?)://[^\s<>\"'\]\)]+|\\\\[\w.\-]+\\[^\s<>\"']*", re.I)
IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
)
IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*(?:%\w+)?", re.I)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b", re.I)
VAT_RE = re.compile(
    r"\b(?:AT|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|HR|HU|IE|IT|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK"
    r"|CHE|GB|TR|TN)[ \-]?U?[0-9A-Z]{0,3}\d{7,11}[A-Z]?\b"
)
CF_RE = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", re.I)
LONG_NUMBER_RE = re.compile(r"(?<![\w.])\+?\d(?:[ .\-/]?\d){8,}(?![\w])")
INTERNAL_FQDN_RE = re.compile(
    r"(?<![\w\-])(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+"
    r"(?:local|lan|corp|internal|intra|intranet|home|localdomain|priv|private|loc|ad)(?![\w\-])",
    re.I,
)
HOST_PREFIX_RE = re.compile(
    r"(?<![\w.\-])(?:srv|svr|dc|fs|sql|db|ws|pc|nb|lt|vm|esxi?|hv|fw|sw|rtr|ap|nas|san|prn"
    r"|exch|plc|hmi|scada)[\-_]?[a-z]*\d{1,4}[a-z]?(?![\w.\-])",
    re.I,
)
HOST_CAPS_RE = re.compile(r"(?<![\w.\-])([A-Z]{3,})\d{2,}[A-Z]?(?![\w.\-])")
_STREET = (
    r"via|viale|v\.le|piazza|p\.zza|piazzale|corso|c\.so|largo|vicolo|strada|località|loc\."
    r"|rue|avenue|boulevard|chemin|allée|impasse"
    r"|ul\.|ulica|al\.|aleja|osiedle"
    r"|cad\.|caddesi|sok\.|sokak|mah\.|mahallesi|bulvarı|blv\."
    r"|street|road"
)
# Il nome della via inizia con la maiuscola e il civico non è una durata
# ("inviato via PEC entro 72 ore" non è un indirizzo).
_DURATION = r"ore|h|giorni|gg|hours?|days?|minuti|min|mesi|anni|settimane|heures|jours|godzin|dni|saat|gün"
STREET_RE = re.compile(
    rf"\b(?i:{_STREET})\s+[{_UP}][^\d,;\n\[\]]{{1,40}}?,?\s*(?:n\.?\s*|no\.?\s*)?\d{{1,4}}[a-zA-Z]?(?:/\d+)?\b"
    rf"(?!\s*(?:(?i:{_DURATION})\b|%))"
)
POSTCODE_CITY_RE = re.compile(rf"\b(?:\d{{5}}|\d{{2}}-\d{{3}})\s+{_NAME_WORD}(?:\s+{_NAME_WORD})?")
TITLED_PERSON_RE = re.compile(rf"\b(?i:{TITLES_BEFORE})\s+({_NAME_WORD}(?:\s+{_NAME_WORD})?)")
PERSON_TITLE_AFTER_RE = re.compile(rf"\b({_NAME_WORD})\s+(?i:{TITLES_AFTER})\b")

_DATE_RE = re.compile(r"\b(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)\d{2}\b")
_REGULATION_RE = re.compile(r"^(?:19|20)\d{2}/\d{1,4}$|^\d{1,4}/(?:19|20)\d{2}$")
_CPV_RE = re.compile(r"^\d{8}-\d$")
_VULN_ID_BEFORE_RE = re.compile(r"(?:CVE|CWE|GHSA|BDU|JVNDB)-$", re.I)
_STANDARD_BEFORE_RE = re.compile(r"(?:ISO|IEC|EN|UNI|NIST|SP|CEI|BS|DIN)[\s/:\-]*$", re.I)

# Regioni per i numeri nazionali senza prefisso internazionale: Italia e i
# paesi dei siti tipici. I numeri con "+" sono riconosciuti da qualunque regione.
PHONE_REGIONS = ("IT", "FR", "PL", "TR", "TN", "DE", "ES", "GB")


def _fold(word: str) -> str:
    """Minuscolo senza accenti (Paweł → pawel, Hüseyin → huseyin)."""
    word = word.lower().replace("ł", "l").replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", word) if not unicodedata.combining(c))


@dataclass(frozen=True)
class _Entity:
    value: str
    kind: str
    key: str  # varianti dello stesso soggetto → stesso token


def _person_variants(first: str, last: str) -> list[str]:
    first, last = " ".join(first.split()), " ".join(last.split())
    if not first or not last:
        return []
    out = [f"{first} {last}", f"{last} {first}", f"{first[0]}. {last}", f"{last} {first[0]}."]
    return [v for v in out if len(v) >= 5]


def _known_entities() -> list[_Entity]:
    """Dizionario delle entità dell'organizzazione (tutti i siti, sempre)."""
    from django.contrib.auth import get_user_model

    from apps.assets.models import Asset, AssetIT, AssetOT
    from apps.governance.models import CommitteeMember
    from apps.incidents.models import NIS2Configuration
    from apps.management_review.models import ReviewParticipant
    from apps.osint.models import OsintEntity, OsintSubdomain
    from apps.pdca.models import PdcaCycle
    from apps.plants.models import BusinessUnit, Plant
    from apps.risk.models import RiskAssessment, RiskMitigationPlan
    from apps.suppliers.models import Supplier

    ents: list[_Entity] = []

    def add(value, kind, key):
        value = " ".join(str(value or "").split())
        if len(value) < 3 or value.isdigit() and len(value) < 6:
            return
        if kind in ("ASSET", "SUPPLIER") and _fold(value) in GENERIC_NAMES:
            return
        ents.append(_Entity(value, kind, key))

    User = get_user_model()
    for pk, first, last, username in User.objects.values_list("pk", "first_name", "last_name", "username"):
        for v in _person_variants(first, last):
            add(v, "PERSON", f"user:{pk}")
        if username and "@" not in username and len(username) >= 4 and _fold(username) not in {"admin", "root", "test", "user", "service"}:
            add(username, "PERSON", f"user:{pk}")

    plants = Plant.objects.order_by("created_at", "pk").values_list("pk", "name", "code", "domain", "legal_entity_vat")
    for i, (pk, name, code, domain, vat) in enumerate(plants, start=1):
        add(name, f"SITE_{i}", f"plant:{pk}")
        add(code, f"SITE_{i}_CODE", f"plantcode:{pk}")
        add(domain, "DOMAIN", f"domain:{_fold(domain or '')}")
        add(vat, "VAT", f"vat:{vat}")
    for pk, name in BusinessUnit.objects.values_list("pk", "name"):
        add(name, "BU", f"bu:{pk}")
    for pk, name in Asset.objects.values_list("pk", "name"):
        add(name, "ASSET", f"asset:{pk}")
    for model in (AssetIT, AssetOT):
        for fqdn, ip in model.objects.values_list("fqdn", "ip_address"):
            add(fqdn, "HOST", f"host:{_fold(fqdn or '')}")
            add(ip, "IP", f"ip:{ip}")
    for pk, name, vat, email, website in Supplier.objects.values_list("pk", "name", "vat_number", "email", "website"):
        add(name, "SUPPLIER", f"supplier:{pk}")
        add(vat, "VAT", f"vat:{vat}")
        add(email, "EMAIL", f"email:{_fold(email or '')}")
        host = re.sub(r"^[a-z]+://", "", website or "", flags=re.I).split("/")[0]
        add(host, "DOMAIN", f"domain:{_fold(host)}")
    for domain, display in OsintEntity.objects.values_list("domain", "display_name"):
        add(domain, "DOMAIN", f"domain:{_fold(domain or '')}")
        add(display, "SUPPLIER", f"osint:{_fold(display or '')}")
    for (sub,) in OsintSubdomain.objects.values_list("subdomain"):
        add(sub, "HOST", f"host:{_fold(sub or '')}")
    free_text_people = (
        CommitteeMember.objects.values_list("full_name", flat=True),
        ReviewParticipant.objects.values_list("full_name", flat=True),
        RiskAssessment.objects.exclude(treatment_owner_external="").values_list("treatment_owner_external", flat=True),
        RiskMitigationPlan.objects.exclude(owner_external="").values_list("owner_external", flat=True),
        PdcaCycle.objects.exclude(action_owner="").values_list("action_owner", flat=True),
        NIS2Configuration.objects.exclude(internal_contact_name="").values_list("internal_contact_name", flat=True),
    )
    for values in free_text_people:
        for name in values:
            add(name, "PERSON", f"person:{_fold(name or '')}")
    for email, phone in NIS2Configuration.objects.values_list("internal_contact_email", "internal_contact_phone"):
        add(email, "EMAIL", f"email:{_fold(email or '')}")
        add(phone, "PHONE", f"phone:{phone}")
    return ents


class _EntityIndex:
    """Le entità compilate in due regex (nomi/codici e domini)."""

    def __init__(self, entities: list[_Entity]):
        self.by_value: dict[str, _Entity] = {}
        domains: list[str] = []
        names: list[str] = []
        for e in sorted(entities, key=lambda x: len(x.value), reverse=True):
            low = e.value.lower()
            if low in self.by_value:
                continue
            self.by_value[low] = e
            (domains if e.kind == "DOMAIN" else names).append(e.value)
        self.names_re = self._compile(names, r"(?<![\w@.\-])", r"(?![\w\-]|\.\w)")
        self.domains_re = self._compile(domains, r"(?<![\w\-@.])(?:[a-z0-9\-]+\.)*", r"(?![\w\-]|\.\w)")
        self.domains = {d.lower() for d in domains}

    @staticmethod
    def _compile(values, before, after):
        if not values:
            return None
        alternation = "|".join(re.escape(v).replace(r"\ ", r"\s+") for v in values)
        return re.compile(f"{before}(?:{alternation}){after}", re.I)

    def entity_for(self, matched: str) -> _Entity | None:
        return self.by_value.get(" ".join(matched.split()).lower())


class Sanitizer:
    """Tokenizza testi destinati all'IA e ripristina i valori nella risposta.

    Un'istanza per richiesta: prompt e system passano dalla stessa istanza,
    così uno stesso valore ha lo stesso token in entrambi e i token non si
    sovrappongono.
    """

    def __init__(self, entities: list[_Entity] | None = None):
        self._entities = entities
        self._index: _EntityIndex | None = None
        self._token_for_key: dict[str, str] = {}
        self._value_for_token: dict[str, str] = {}
        self._counters: Counter = Counter()
        self.counts: Counter = Counter()

    # ── API ────────────────────────────────────────────────────────────────
    def sanitize(self, context: dict, plant_ids: list | None = None) -> tuple[dict, dict]:
        """`plant_ids` resta per compatibilità: il dizionario copre sempre
        tutta l'organizzazione (un sito non citato nel perimetro della
        richiesta può comparire comunque nel testo libero)."""
        text = self.tokenize(str(context.get("text", "")))
        return {**context, "text": text}, dict(self._value_for_token)

    def desanitize(self, text: str, token_map: dict) -> str:
        for token in sorted(token_map, key=len, reverse=True):
            text = re.sub(re.escape(token), lambda _m, v=token_map[token]: v, text, flags=re.I)
        return text

    @property
    def token_map(self) -> dict:
        return dict(self._value_for_token)

    def tokenize(self, text: str) -> str:
        if not text:
            return text
        index = self._get_index()
        steps = (
            (EMAIL_RE, "EMAIL", None),
            (URL_RE, "URL", None),
            (IPV6_RE, "IP", _valid_ipv6),
            (IPV4_RE, "IP", None),
            (IBAN_RE, "IBAN", _looks_like_iban),
            (VAT_RE, "VAT", None),
            (CF_RE, "TAXID", None),
        )
        for pattern, kind, check in steps:
            text = self._replace(text, pattern, kind, check)
        text = self._replace_phones(text)
        if index.domains_re is not None:
            text = self._replace(text, index.domains_re, "DOMAIN", None)
        if index.names_re is not None:
            text = self._replace_entities(text, index)
        text = self._replace(text, INTERNAL_FQDN_RE, "HOST", None)
        text = self._replace(text, HOST_PREFIX_RE, "HOST", None)
        text = self._replace(text, HOST_CAPS_RE, "HOST", _not_standard_code)
        text = self._replace(text, STREET_RE, "ADDRESS", None)
        text = self._replace(text, POSTCODE_CITY_RE, "ADDRESS", None, context_check=_postcode_city)
        text = self._replace_group(text, TITLED_PERSON_RE, "PERSON")
        text = self._replace_group(text, PERSON_TITLE_AFTER_RE, "PERSON")
        text = self._replace_name_pairs(text)
        text = self._replace(
            text, LONG_NUMBER_RE, "NUMBER", _is_identifier_number,
            context_check=lambda seg, m: not _VULN_ID_BEFORE_RE.search(seg[: m.start()]),
        )
        return text

    # ── interni ────────────────────────────────────────────────────────────
    def _get_index(self) -> _EntityIndex:
        if self._index is None:
            if self._entities is None:
                self._entities = _known_entities()
            self._index = _EntityIndex(self._entities)
        return self._index

    def _token(self, kind: str, value: str, key: str | None = None) -> str:
        key = key or f"{kind}:{' '.join(value.split()).lower()}"
        token = self._token_for_key.get(key)
        if token is None:
            if kind.startswith("SITE_"):
                token = f"[{kind}]"  # posizione stabile del sito nell'organizzazione
            else:
                self._counters[kind] += 1
                token = f"[{kind}_{self._counters[kind]}]"
            self._token_for_key[key] = token
            self._value_for_token[token] = value
        self.counts[kind.split("_")[0] if kind.startswith("SITE_") else kind] += 1
        return token

    @staticmethod
    def _outside_tokens(text: str, fn) -> str:
        parts, last = [], 0
        for m in TOKEN_RE.finditer(text):
            parts.append(fn(text[last:m.start()]))
            parts.append(m.group())
            last = m.end()
        parts.append(fn(text[last:]))
        return "".join(parts)

    def _replace(self, text, pattern, kind, check, context_check=None):
        def on_segment(segment):
            def repl(m):
                value = m.group()
                if check is not None and not check(value):
                    return value
                if context_check is not None and not context_check(segment, m):
                    return value
                return self._token(kind, value)
            return pattern.sub(repl, segment)
        return self._outside_tokens(text, on_segment)

    def _replace_group(self, text, pattern, kind):
        def on_segment(segment):
            def repl(m):
                name = m.group(1)
                if _fold(name.split()[0]) in NOT_SURNAMES:
                    return m.group()
                start, end = m.span(1)
                base = m.start()
                whole = m.group()
                return whole[: start - base] + self._token(kind, name) + whole[end - base:]
            return pattern.sub(repl, segment)
        return self._outside_tokens(text, on_segment)

    def _replace_name_pairs(self, text):
        """Coppie "Nome Cognome" / "Cognome Nome" con un nome proprio comune.
        Scansione parola per parola: con finditer "Il Mario Rossi" consumava
        "Il Mario" e lasciava passare il nome."""
        word_re = re.compile(_NAME_WORD)

        def on_segment(segment):
            words = list(word_re.finditer(segment))
            out, last, i = [], 0, 0
            while i < len(words) - 1:
                a, b = words[i], words[i + 1]
                gap = segment[a.end():b.start()]
                value = f"{a.group()} {b.group()}"
                if gap.strip() == "" and "\n" not in gap and _is_person_name(value):
                    out.append(segment[last:a.start()])
                    out.append(self._token("PERSON", segment[a.start():b.end()]))
                    last = b.end()
                    i += 2
                else:
                    i += 1
            out.append(segment[last:])
            return "".join(out)
        return self._outside_tokens(text, on_segment)

    def _replace_entities(self, text, index: _EntityIndex):
        def on_segment(segment):
            def repl(m):
                entity = index.entity_for(m.group())
                if entity is None:
                    return m.group()
                return self._token(entity.kind, entity.value, entity.key)
            return index.names_re.sub(repl, segment)
        return self._outside_tokens(text, on_segment)

    def _replace_phones(self, text):
        def on_segment(segment):
            spans = {}
            for region in PHONE_REGIONS:
                for match in phonenumbers.PhoneNumberMatcher(segment, region, leniency=phonenumbers.Leniency.POSSIBLE):
                    raw = match.raw_string
                    digits = re.sub(r"\D", "", raw)
                    if len(digits) < 8 or _DATE_RE.search(raw) or _CPV_RE.match(raw.strip()):
                        continue
                    if _VULN_ID_BEFORE_RE.search(segment[: match.start]):
                        continue
                    # Senza "+" e senza spazi è un codice (P.IVA, NIP, PESEL):
                    # lo prende la regola dei numeri, con l'etichetta giusta.
                    if not raw.startswith("+") and " " not in raw:
                        continue
                    spans.setdefault(match.start, match.end)
            if not spans:
                return segment
            out, last = [], 0
            for start in sorted(spans):
                end = spans[start]
                if start < last:
                    continue
                out.append(segment[last:start])
                out.append(self._token("PHONE", segment[start:end]))
                last = end
            out.append(segment[last:])
            return "".join(out)
        return self._outside_tokens(text, on_segment)


def _valid_ipv6(value: str) -> bool:
    try:
        ipaddress.IPv6Address(value.split("%")[0].rstrip("."))
        return True
    except ValueError:
        return False


def _looks_like_iban(value: str) -> bool:
    compact = value.replace(" ", "")
    return len(compact) >= 15 and sum(c.isdigit() for c in compact) >= 8


def _not_standard_code(value: str) -> bool:
    letters = re.match(r"[A-Z]+", value).group()
    return _fold(letters) not in STANDARD_PREFIXES


def _postcode_city(segment: str, m) -> bool:
    """"20100 Milano" sì; "ISO 27001 Information" e "50000 Euro" no."""
    city = m.group().split(None, 1)[1]
    if _fold(city.split()[0]) in CURRENCY_WORDS:
        return False
    return not _STANDARD_BEFORE_RE.search(segment[: m.start()])


def _is_person_name(value: str) -> bool:
    first, last = value.split(None, 1)
    a, b = _fold(first), _fold(last)
    if a in NOT_SURNAMES or b in NOT_SURNAMES:
        return False
    return a in FIRST_NAMES or (b in FIRST_NAMES and a not in FIRST_NAMES)


def _is_identifier_number(value: str) -> bool:
    raw = value.strip()
    if _DATE_RE.search(raw) or _REGULATION_RE.match(raw) or _CPV_RE.match(raw):
        return False
    return sum(c.isdigit() for c in raw) >= 9


# ── Guardia in uscita ──────────────────────────────────────────────────────
_GUARD_CHECKS = (
    ("EMAIL", re.compile(r"@[\w\-]+(?:\.[\w\-]+)*\.[A-Za-z]{2,}")),
    ("URL", re.compile(r"://|\\\\[\w.\-]+\\")),
    ("IP", IPV4_RE),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,}\b")),
    ("TAXID", CF_RE),
    ("HOST", INTERNAL_FQDN_RE),
)


@dataclass
class GuardResult:
    blocked: bool
    findings: dict

    def as_dict(self) -> dict:
        return {"blocked": self.blocked, "findings": self.findings}


class EgressGuard:
    """Ricontrolla un testo già tokenizzato prima che esca verso il cloud.

    Indipendente dalle sostituzioni del Sanitizer: cerca residui con regole più
    larghe (qualsiasi "@dominio", "://", IPv4, IBAN compatti, codici fiscali,
    domini interni, entità del dizionario, numeri identificativi). Se trova
    qualcosa il testo non deve uscire. Restituisce solo conteggi per tipo,
    mai i valori: è ciò che può finire nei log.
    """

    def __init__(self, sanitizer: Sanitizer):
        self._sanitizer = sanitizer

    def check(self, *texts: str) -> GuardResult:
        findings: Counter = Counter()
        index = self._sanitizer._get_index()
        for text in texts:
            if not text:
                continue
            outside = TOKEN_RE.sub(" ", text)
            for kind, pattern in _GUARD_CHECKS:
                findings[kind] += len(pattern.findall(outside))
            for m in LONG_NUMBER_RE.finditer(outside):
                if _is_identifier_number(m.group()):
                    findings["NUMBER"] += 1
            for regex in (index.names_re, index.domains_re):
                if regex is not None:
                    findings["ENTITY"] += sum(1 for m in regex.finditer(outside) if m.group().strip())
        findings = {k: v for k, v in findings.items() if v}
        return GuardResult(blocked=bool(findings), findings=findings)
