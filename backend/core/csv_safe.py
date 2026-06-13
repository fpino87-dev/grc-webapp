"""Protezione contro CSV formula injection (OWASP) per tutti gli export CSV.

Un valore che inizia con `= + - @`, tab o CR viene interpretato come formula da
Excel/LibreOffice/Sheets all'apertura del file. Prefissando un apostrofo la cella
resta testo. I numeri (anche negativi, es. `-5`, `+3.2`, notazione esponenziale)
NON vengono alterati per non corrompere le colonne numeriche.

Uso: sostituire `csv.writer(f)` con `safe_writer(f)` e
`csv.DictWriter(f, fieldnames=...)` con `safe_dict_writer(f, fieldnames=...)`.
L'API (`writerow`/`writerows`/`writeheader`) è identica a quella stdlib.
"""
import csv as _csv
import re

_TRIGGER = ("=", "+", "-", "@", "\t", "\r")
_NUMERIC = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def csv_safe(value) -> str:
    """Restituisce il valore come stringa, neutralizzando le formule."""
    s = "" if value is None else str(value)
    if s and s[0] in _TRIGGER and not _NUMERIC.match(s):
        return "'" + s
    return s


class _SafeWriter:
    def __init__(self, fileobj, **kwargs):
        self._w = _csv.writer(fileobj, **kwargs)

    def writerow(self, row):
        self._w.writerow([csv_safe(c) for c in row])

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class _SafeDictWriter:
    def __init__(self, fileobj, fieldnames, **kwargs):
        self._fieldnames = list(fieldnames)
        self._w = _csv.DictWriter(fileobj, fieldnames=self._fieldnames, **kwargs)

    def writeheader(self):
        # Le intestazioni sono stringhe applicative statiche: le sanifichiamo
        # comunque per coerenza, senza alterarne il significato.
        self._w.writerow({k: csv_safe(k) for k in self._fieldnames})

    def writerow(self, row):
        self._w.writerow({k: csv_safe(v) for k, v in row.items()})

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def safe_writer(fileobj, **kwargs):
    return _SafeWriter(fileobj, **kwargs)


def safe_dict_writer(fileobj, fieldnames, **kwargs):
    return _SafeDictWriter(fileobj, fieldnames=fieldnames, **kwargs)
