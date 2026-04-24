"""
Report PDF audit-ready per fornitori — Fase 6.

Genera un report che documenta la valutazione del rischio fornitore con:
- dati anagrafici e campi ACN (NIS2, CPV, concentrazione)
- valutazione interna corrente (6 score, weighted_score, classe) con snapshot pesi
- storico valutazioni interne
- assessment esterni approvati (inclusa validità)
- risk_adj e spiegazione (bump NIS2 applicato o no)
- riferimenti normativi: NIS2 Art.21.2(d), TISAX 5.2.x, ISO27001 A.5.19–A.5.21
"""
from __future__ import annotations

import datetime
import io
from typing import Optional

from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from .models import (
    Supplier,
    SupplierAssessment,
    SupplierEvaluationConfig,
    SupplierInternalEvaluation,
)


_RISK_COLORS = {
    "basso": colors.HexColor("#16a34a"),
    "medio": colors.HexColor("#ca8a04"),
    "alto": colors.HexColor("#ea580c"),
    "critico": colors.HexColor("#dc2626"),
}

_CRITERION_LABELS = {
    "ict": "Fornitura ICT strutturale (criterio a)",
    "non_fungibile": "Non fungibilità (criterio b)",
    "entrambi": "Entrambi (a + b)",
    "": "—",
}

_THRESHOLD_LABELS = {
    "bassa": "Bassa (<20%)",
    "media": "Media (20–50%)",
    "critica": "Critica (>50%)",
    "nd": "N/D",
}


def _fmt_date(d: Optional[datetime.date | datetime.datetime]) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%d %H:%M")
    return d.strftime("%Y-%m-%d")


def _risk_badge(cls: str, styles) -> Paragraph:
    color = _RISK_COLORS.get(cls, colors.HexColor("#6b7280"))
    style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        textColor=colors.white,
        backColor=color,
        alignment=1,
        fontSize=9,
        leading=11,
    )
    return Paragraph(f"<b>&nbsp;{(cls or 'N/D').upper()}&nbsp;</b>", style)


def build_supplier_risk_report(supplier: Supplier) -> bytes:
    """Restituisce il PDF (bytes) del report di rischio del fornitore."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"Report rischio fornitore — {supplier.name}",
        author="GRC Webapp",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1Small", parent=styles["Heading1"], fontSize=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="H2Small", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#374151")))
    styles.add(ParagraphStyle(name="Footnote", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#6b7280")))

    config = SupplierEvaluationConfig.get_solo()
    current_eval = (
        SupplierInternalEvaluation.objects.filter(
            supplier=supplier, is_current=True, deleted_at__isnull=True
        ).first()
    )
    history = (
        SupplierInternalEvaluation.objects.filter(
            supplier=supplier, deleted_at__isnull=True
        ).order_by("-evaluated_at")[:10]
    )
    latest_assessment = (
        SupplierAssessment.objects.filter(
            supplier=supplier, status="approvato", deleted_at__isnull=True
        ).order_by("-assessment_date").first()
    )

    story = []

    # Intestazione
    story.append(Paragraph(f"Report di rischio — Fornitore", styles["H1Small"]))
    story.append(Paragraph(f"<b>{supplier.name}</b>", styles["Heading3"]))
    story.append(Paragraph(
        f"Data report: {_fmt_date(timezone.now())} · "
        f"Conformità: NIS2 Art. 21.2(d), TISAX 5.2.x, ISO/IEC 27001 A.5.19–A.5.21",
        styles["Small"],
    ))
    story.append(Spacer(1, 6 * mm))

    # Anagrafica
    story.append(Paragraph("1. Anagrafica fornitore", styles["H2Small"]))
    anagrafica = [
        ["Denominazione", supplier.name],
        ["Codice Fiscale / P.IVA", supplier.vat_number or "—"],
        ["Paese sede legale", supplier.country or "—"],
        ["Email referente", supplier.email or "—"],
        ["Stato", supplier.status],
        ["Note", (supplier.notes or "—")[:300]],
    ]
    story.append(_make_kv_table(anagrafica))

    # Campi ACN / NIS2
    story.append(Paragraph("2. Campi ACN / NIS2 (Delibera 127434/2026)", styles["H2Small"]))
    cpv_codes = supplier.cpv_codes or []
    cpv_str = "\n".join(
        f"• {c.get('code', '')} — {c.get('label', '')}" if isinstance(c, dict) else str(c)
        for c in cpv_codes
    ) or "—"
    acn = [
        ["Descrizione fornitura", (supplier.description or "—")[:500]],
        ["Codici CPV", cpv_str],
        ["Rilevante NIS2", "Sì" if supplier.nis2_relevant else "No"],
        ["Criterio NIS2", _CRITERION_LABELS.get(supplier.nis2_relevance_criterion, supplier.nis2_relevance_criterion or "—")],
        ["% Concentrazione", f"{supplier.supply_concentration_pct}%" if supplier.supply_concentration_pct is not None else "—"],
        ["Soglia TPRM", _THRESHOLD_LABELS.get(supplier.concentration_threshold, "—")],
    ]
    story.append(_make_kv_table(acn))

    # Rischio Adj — banner principale
    story.append(Paragraph("3. Rischio aggiustato (Risk Adj)", styles["H2Small"]))
    risk_explanation_lines = _risk_adj_explanation(supplier, current_eval, latest_assessment, config)
    risk_data = [
        ["Classe interna", supplier.internal_risk_level or "—"],
        ["Classe assessment esterno valido",
         _assessment_class_cell(latest_assessment, config)],
        ["Bump NIS2 + concentrazione critica applicato",
         _bump_explanation(supplier, config)],
        ["Rischio aggiustato (risk_adj)", supplier.risk_adj or "—"],
        ["Ultimo aggiornamento", _fmt_date(supplier.risk_adj_updated_at)],
    ]
    story.append(_make_kv_table(risk_data))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Metodologia:</b>", styles["Small"]))
    for line in risk_explanation_lines:
        story.append(Paragraph(f"• {line}", styles["Small"]))

    # Valutazione interna corrente
    story.append(PageBreak())
    story.append(Paragraph("4. Valutazione interna corrente", styles["H2Small"]))
    if current_eval:
        story.append(_render_internal_evaluation_table(current_eval, config))
        if current_eval.notes:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(f"<i>Note:</i> {current_eval.notes}", styles["Small"]))
    else:
        story.append(Paragraph("Nessuna valutazione interna registrata.", styles["Normal"]))

    # Storico
    story.append(Paragraph("5. Storico valutazioni interne (ultime 10)", styles["H2Small"]))
    if history:
        story.append(_render_history_table(history))
    else:
        story.append(Paragraph("Nessuno storico.", styles["Normal"]))

    # Assessment esterni
    story.append(Paragraph("6. Assessment esterni approvati", styles["H2Small"]))
    assessments = SupplierAssessment.objects.filter(
        supplier=supplier, status="approvato", deleted_at__isnull=True
    ).order_by("-assessment_date")[:5]
    if assessments:
        story.append(_render_assessments_table(assessments, config))
    else:
        story.append(Paragraph("Nessun assessment esterno approvato.", styles["Normal"]))

    # Riferimenti normativi
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("7. Riferimenti normativi", styles["H2Small"]))
    for ref in _regulatory_references():
        story.append(Paragraph(f"• {ref}", styles["Small"]))

    # Footer
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Documento generato automaticamente dalla GRC Webapp. I dati riflettono lo stato "
        f"al {_fmt_date(timezone.now())}. Utilizzare in abbinamento ad audit trail (M10) per la verifica cronologica.",
        styles["Footnote"],
    ))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def _make_kv_table(rows: list) -> Table:
    table = Table(rows, colWidths=[55 * mm, 120 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _render_internal_evaluation_table(ev: SupplierInternalEvaluation, config: SupplierEvaluationConfig) -> Table:
    weights = ev.weights_snapshot or config.weights
    labels = config.parameter_labels or {}
    rows = [["Parametro", "Peso", "Score (1–5)", "Livello"]]
    for key in ("impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"):
        score = getattr(ev, f"score_{key}")
        weight = weights.get(key, 0)
        label_data = labels.get(key, {})
        level_label = (label_data.get("levels") or ["", "", "", "", ""])[max(0, min(score - 1, 4))]
        rows.append([
            label_data.get("name", key.capitalize()),
            f"{float(weight) * 100:.0f}%",
            str(score),
            level_label,
        ])
    rows.append(["", "", "Weighted score", f"{float(ev.weighted_score):.3f}"])
    rows.append(["", "", "Classe di rischio", (ev.risk_class or "—").upper()])

    table = Table(rows, colWidths=[55 * mm, 20 * mm, 25 * mm, 75 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("BACKGROUND", (2, -1), (-1, -1),
         _RISK_COLORS.get(ev.risk_class, colors.HexColor("#6b7280"))),
        ("TEXTCOLOR", (2, -1), (-1, -1), colors.white),
        ("FONTNAME", (2, -2), (-1, -1), "Helvetica-Bold"),
    ]))
    return table


def _render_history_table(history) -> Table:
    rows = [["Data", "Utente", "Weighted", "Classe", "Corrente", "Note"]]
    for h in history:
        rows.append([
            _fmt_date(h.evaluated_at),
            (h.evaluated_by.get_full_name() if h.evaluated_by else "") or (h.evaluated_by.email if h.evaluated_by else "—"),
            f"{float(h.weighted_score):.3f}",
            (h.risk_class or "").upper(),
            "✓" if h.is_current else "",
            (h.notes or "")[:60],
        ])
    table = Table(rows, colWidths=[28 * mm, 35 * mm, 20 * mm, 20 * mm, 18 * mm, 54 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _render_assessments_table(assessments, config: SupplierEvaluationConfig) -> Table:
    validity_cutoff = timezone.now().date() - datetime.timedelta(days=config.assessment_validity_months * 30)
    rows = [["Data", "Score", "Classe derivata", "Validità", "Approvato da", "Note"]]
    for a in assessments:
        valid = a.assessment_date >= validity_cutoff
        score = a.score_overall if a.score_overall is not None else "—"
        rows.append([
            _fmt_date(a.assessment_date),
            str(score),
            _assessment_class_cell(a, config),
            "VALIDA" if valid else "SCADUTA",
            (a.reviewed_by.get_full_name() if a.reviewed_by else "") or (a.reviewed_by.email if a.reviewed_by else "—"),
            (a.review_notes or "")[:60],
        ])
    table = Table(rows, colWidths=[28 * mm, 15 * mm, 30 * mm, 22 * mm, 35 * mm, 45 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _assessment_class_cell(assessment: Optional[SupplierAssessment], config: SupplierEvaluationConfig) -> str:
    if assessment is None:
        return "—"
    if assessment.score_overall is None:
        return "N/D"
    s = assessment.score_overall
    if s >= 75: return "basso"
    if s >= 50: return "medio"
    if s >= 25: return "alto"
    return "critico"


def _bump_explanation(supplier: Supplier, config: SupplierEvaluationConfig) -> str:
    active = (
        config.nis2_concentration_bump
        and supplier.nis2_relevant
        and supplier.concentration_threshold == "critica"
    )
    if not config.nis2_concentration_bump:
        return "No (policy di bump disattivata in configurazione)"
    if not supplier.nis2_relevant:
        return "No (fornitore non marcato NIS2 rilevante)"
    if supplier.concentration_threshold != "critica":
        return f"No (concentrazione: {_THRESHOLD_LABELS.get(supplier.concentration_threshold, '—')})"
    return "Sì — classe incrementata di +1 livello"


def _risk_adj_explanation(supplier, current_eval, latest_assessment, config) -> list:
    lines = [
        "Formula B — worst-case conservativo: risk_adj = max(classe_interna, classe_assessment_esterno_valido)",
        f"Validità assessment esterno configurata: {config.assessment_validity_months} mesi",
        f"Peso parametri (somma = 1.00): {', '.join(f'{k}={v:.2f}' for k, v in config.weights.items())}",
        f"Soglie classi: basso < {config.risk_thresholds.get('medio', 2.0)} ≤ medio < "
        f"{config.risk_thresholds.get('alto', 3.0)} ≤ alto < "
        f"{config.risk_thresholds.get('critico', 4.0)} ≤ critico",
    ]
    if config.nis2_concentration_bump:
        lines.append(
            "Bump NIS2 attivo: fornitori NIS2-rilevanti con concentrazione critica (>50%) "
            "subiscono +1 classe (saturazione a 'critico')."
        )
    return lines


def _regulatory_references() -> list:
    return [
        "NIS2 (Dir. UE 2022/2555) — Art. 21.2(d): misure di gestione del rischio "
        "per la supply chain, proporzionate alla criticità del fornitore.",
        "ACN Delibera n. 127434 del 13/04/2026 — obblighi di tracciabilità della "
        "catena di fornitura ICT strutturale per soggetti NIS2.",
        "TISAX — Sezione 5.2.x: Information security in supplier relationships, "
        "valutazione preventiva e periodica delle terze parti.",
        "ISO/IEC 27001:2022 — Controlli A.5.19 (Information security in supplier "
        "relationships), A.5.20 (Addressing information security within supplier "
        "agreements), A.5.21 (Managing information security in the ICT supply chain).",
    ]
