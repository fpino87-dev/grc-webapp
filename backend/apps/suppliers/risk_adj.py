"""
Risk Adj service — Fase 3.

Calcola il rischio aggiustato (`Supplier.risk_adj`) combinando:
  - rischio interno corrente (ultima `SupplierInternalEvaluation` con is_current=True)
  - rischio esterno dall'ultimo assessment approvato entro validità configurata

Formula B (max conservativo):
    base_class = max(rischio_interno, rischio_esterno_se_valido)

Bump NIS2 (se config.nis2_concentration_bump = True):
    Se supplier.nis2_relevant AND supplier.concentration_threshold == "critica"
    la classe sale di +1 (basso→medio, medio→alto, alto→critico, critico→critico).

Rationale compliance:
  - NIS2 Art. 21.2(d): supply chain risk management proporzionale alla criticità
  - TISAX 5.2.x: valutazione rischio terze parti
  - ISO 27001 A.5.19-A.5.21: information security in supplier relationships
"""
from __future__ import annotations

import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
)


# Mapping ordinale classi di rischio — l'ordine è semanticamente crescente.
_CLASS_ORDER = ("basso", "medio", "alto", "critico")
_CLASS_RANK = {c: i for i, c in enumerate(_CLASS_ORDER)}


def _rank(cls: str) -> int:
    return _CLASS_RANK.get(cls, -1)


def _class_from_rank(rank: int) -> str:
    rank = max(0, min(rank, len(_CLASS_ORDER) - 1))
    return _CLASS_ORDER[rank]


def _assessment_to_class(score_overall: Optional[int]) -> Optional[str]:
    """Mappa lo `score_overall` (0–100) alla classe di rischio interna (basso/medio/alto/critico)."""
    if score_overall is None:
        return None
    if score_overall >= 75:
        return "basso"
    if score_overall >= 50:
        return "medio"
    if score_overall >= 25:
        return "alto"
    return "critico"


def _latest_valid_external_class(supplier: Supplier, validity_months: int) -> Optional[str]:
    """
    Ritorna la classe di rischio dall'ultimo assessment APPROVATO entro validità.
    None se nessun assessment valido disponibile.
    """
    cutoff = timezone.now().date() - datetime.timedelta(days=validity_months * 30)
    latest = (
        SupplierAssessment.objects.filter(
            supplier=supplier,
            status="approvato",
            assessment_date__gte=cutoff,
            deleted_at__isnull=True,
        )
        .order_by("-assessment_date")
        .first()
    )
    if latest is None:
        return None
    return _assessment_to_class(latest.score_overall)


def _current_internal_class(supplier: Supplier) -> Optional[str]:
    ev = (
        SupplierInternalEvaluation.objects.filter(
            supplier=supplier, is_current=True, deleted_at__isnull=True
        )
        .order_by("-evaluated_at")
        .first()
    )
    return ev.risk_class if ev else None


@transaction.atomic
def recompute_risk_adj(supplier: Supplier) -> Supplier:
    """
    Ricalcola `supplier.internal_risk_level` e `supplier.risk_adj`.

    - internal_risk_level = classe della valutazione interna corrente (o "" se assente)
    - risk_adj = max(interno, esterno_valido) + bump NIS2 se applicabile
      Se non c'è né interno né esterno valido, risk_adj resta vuoto.
    """
    config = SupplierEvaluationConfig.get_solo()

    internal_class = _current_internal_class(supplier)
    external_class = _latest_valid_external_class(supplier, config.assessment_validity_months)

    supplier.internal_risk_level = internal_class or ""

    candidates = [c for c in (internal_class, external_class) if c]
    if not candidates:
        supplier.risk_adj = ""
        supplier.risk_adj_updated_at = timezone.now()
        supplier.save(update_fields=[
            "internal_risk_level", "risk_adj", "risk_adj_updated_at", "updated_at"
        ])
        return supplier

    base_rank = max(_rank(c) for c in candidates)

    bump = (
        config.nis2_concentration_bump
        and supplier.nis2_relevant
        and supplier.concentration_threshold == "critica"
    )
    final_rank = base_rank + (1 if bump else 0)

    supplier.risk_adj = _class_from_rank(final_rank)
    supplier.risk_adj_updated_at = timezone.now()
    supplier.save(update_fields=[
        "internal_risk_level", "risk_adj", "risk_adj_updated_at", "updated_at"
    ])
    return supplier


def recompute_expired_risk_adj() -> int:
    """
    Task nightly: ricalcola risk_adj per tutti i fornitori con assessment
    approvati che hanno appena scavalcato la soglia di validità (o potrebbero averla fatto).
    Ritorna il numero di fornitori aggiornati.
    """
    count = 0
    for supplier in Supplier.objects.filter(status="attivo", deleted_at__isnull=True):
        before = (supplier.internal_risk_level, supplier.risk_adj)
        recompute_risk_adj(supplier)
        after = (supplier.internal_risk_level, supplier.risk_adj)
        if before != after:
            count += 1
    return count
