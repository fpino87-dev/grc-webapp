"""
Espansione gerarchica dei framework normativi.

Regola TISAX (VDA ISA 6.0):
    L2     -> [L2]
    L3     -> [L2, L3]            (L3 estende L2: stessi controlli L2 + extra)
    PROTO  -> [L2, L3, PROTO]     (Prototype Protection presuppone IS L2+L3)

I framework non-TISAX (ISO27001, NIS2, ACN_NIS2, ...) passano invariati.

Single source of truth: usata sia dal pack builder (`audit_pack.py`) sia dal
seeding degli `EvidenceItem` (`services.py`) sia dalla validazione automatica
(`validation.py`). Modificare la regola qui significa propagarla ovunque.
"""
from __future__ import annotations


def expand_tisax(codes: list[str] | tuple[str, ...] | None) -> list[str]:
    """
    Espande la lista di codici framework applicando la gerarchia TISAX.

    - `TISAX_L3` implica `TISAX_L2`
    - `TISAX_PROTO` implica `TISAX_L2` + `TISAX_L3`

    Output ordinato (sort) e dedotto. Codici non-TISAX passano invariati.
    """
    expanded: set[str] = set(codes or [])
    if "TISAX_PROTO" in expanded:
        expanded |= {"TISAX_L2", "TISAX_L3"}
    if "TISAX_L3" in expanded:
        expanded.add("TISAX_L2")
    return sorted(expanded)
