"""
Normalizzazione di P.IVA e ragione sociale per il rilevamento dei duplicati
fornitore. Funzioni pure (nessun accesso DB): usate dal model (campo
`vat_normalized`), dal service `find_supplier_duplicates` e dalla migrazione.
"""
import re
import unicodedata

# Prefisso IVA UE diverso dal codice ISO paese.
_VAT_PREFIX_BY_COUNTRY = {"GR": "EL"}

# Forme societarie / suffissi rimossi in coda alla ragione sociale
# (dopo aver tolto i punti: "S.r.l." → "srl", "Sp. z o.o." → "sp z oo").
_LEGAL_FORM_TOKENS = {
    # IT
    "srl", "srls", "spa", "sapa", "sas", "snc", "ss", "scarl", "scrl", "scpa",
    "stp", "coop", "soc", "societa", "unipersonale", "c", "e",
    # EN
    "ltd", "limited", "llc", "llp", "inc", "incorporated", "corp", "corporation",
    "plc", "co", "company",
    # DE / AT / CH
    "gmbh", "ag", "kg", "ohg", "ug", "mbh", "und",
    # FR / BE / ES / PT
    "sa", "sarl", "sasu", "eurl", "sca", "sl", "slu", "lda",
    # NL / Nordics
    "bv", "nv", "ab", "as", "oy", "aps",
    # PL / CZ / HU / TR
    "sp", "z", "oo", "sk", "sro", "kft", "zrt", "ltdsti", "sti",
}


def normalize_vat(vat: str | None, country: str | None = "") -> str:
    """Forma canonica della P.IVA / codice fiscale per il confronto.

    Maiuscolo, solo caratteri alfanumerici, senza il prefisso IVA del paese del
    fornitore: `IT 0123.4567-890` e `01234567890` (paese IT) coincidono.
    """
    if not vat:
        return ""
    value = re.sub(r"[^0-9A-Z]", "", vat.upper())
    country = (country or "").strip().upper()
    prefix = _VAT_PREFIX_BY_COUNTRY.get(country, country)
    if len(prefix) == 2 and value.startswith(prefix) and len(value) > 2:
        rest = value[2:]
        # IT: il prefisso si toglie solo davanti a una P.IVA numerica, mai da
        # un codice fiscale alfanumerico di persona fisica.
        if prefix != "IT" or rest.isdigit():
            value = rest
    return value


def normalize_name(name: str | None) -> str:
    """Forma canonica della ragione sociale: minuscolo, senza accenti né
    punteggiatura, spazi compattati, forme societarie in coda rimosse.

    `ROSSI S.r.l.`, `Rossi srl` e `Rossi` coincidono. Se il nome è composto
    solo da forme societarie resta la forma senza rimozione.
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[.'’`]", "", text)          # s.r.l. → srl, reso' → reso
    text = re.sub(r"[^0-9a-z]+", " ", text).strip()
    tokens = text.split()
    stripped = list(tokens)
    while stripped and stripped[-1] in _LEGAL_FORM_TOKENS:
        stripped.pop()
    return " ".join(stripped or tokens)
