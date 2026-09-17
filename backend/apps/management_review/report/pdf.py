"""Renderer PDF della relazione (reportlab), stesso contenuto dell'HTML."""
from django.utils.translation import gettext as _
import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .builder import build_report

PRIMARY = colors.HexColor("#1e40af")
TONES = {
    "red": colors.HexColor("#dc2626"), "orange": colors.HexColor("#d97706"),
    "green": colors.HexColor("#16a34a"), "muted": colors.HexColor("#6b7280"),
}
GREY = colors.HexColor("#6b7280")

# DejaVu copre polacco e turco; Vera (inclusa in reportlab) è il ripiego se il
# pacchetto fonts-dejavu-core non è installato nell'immagine.
_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]
_fonts = None


def _register_fonts() -> tuple[str, str]:
    global _fonts
    if _fonts:
        return _fonts
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    rl_fonts = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    candidates = _FONT_CANDIDATES + [(os.path.join(rl_fonts, "Vera.ttf"), os.path.join(rl_fonts, "VeraBd.ttf"))]
    for regular, bold in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("MR-Regular", regular))
            pdfmetrics.registerFont(TTFont("MR-Bold", bold))
            _fonts = ("MR-Regular", "MR-Bold")
            return _fonts
    _fonts = ("Helvetica", "Helvetica-Bold")
    return _fonts


def _styles():
    regular, bold = _register_fonts()
    base = ParagraphStyle("base", fontName=regular, fontSize=9, leading=12)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=7.5, leading=9.5),
        "cell": ParagraphStyle("cell", parent=base, fontSize=7.5, leading=9.5),
        "th": ParagraphStyle("th", parent=base, fontName=bold, fontSize=7.5, leading=9.5, textColor=colors.white),
        "h1": ParagraphStyle("h1", parent=base, fontName=bold, fontSize=16, leading=20, textColor=PRIMARY),
        "sub": ParagraphStyle("sub", parent=base, fontSize=8.5, textColor=GREY, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontName=bold, fontSize=11.5, leading=15, textColor=PRIMARY,
                             spaceBefore=12, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base, fontName=bold, fontSize=8.5, leading=11, spaceBefore=6, spaceAfter=2),
        "kpi_v": ParagraphStyle("kpi_v", parent=base, fontName=bold, fontSize=14, leading=17, alignment=TA_CENTER,
                                textColor=PRIMARY),
        "kpi_l": ParagraphStyle("kpi_l", parent=base, fontSize=7, leading=9, alignment=TA_CENTER, textColor=GREY),
        "note": ParagraphStyle("note", parent=base, fontSize=7.5, leading=10, textColor=GREY),
        "bold": bold,
    }


def _text(value) -> str:
    """Escape XML per i Paragraph di reportlab, a capo preservati."""
    return escape(str(value)).replace("\n", "<br/>")


def _cell(c, st):
    if isinstance(c, dict):
        text = _text(c.get("text", ""))
        if c.get("bold"):
            text = f"<font name='{st['bold']}'>{text}</font>"
        if c.get("tone"):
            text = f"<font color='{TONES[c['tone']].hexval()}'>{text}</font>"
        return Paragraph(text, st["cell"])
    return Paragraph(_text(c), st["cell"])


def _col_widths(b, width) -> list[float]:
    """Larghezze proporzionali al contenuto: testi lunghi (descrizioni) prendono
    spazio, date e numeri restano strette, le intestazioni non si spezzano."""
    def _len(c):
        return len(str(c.get("text", "") if isinstance(c, dict) else c))

    weights = []
    for i, header in enumerate(b["headers"]):
        # intestazione su al massimo due righe senza spezzare le parole
        longest_word = max((len(w) for w in header.split()), default=4)
        header_need = max(longest_word, (len(header) + 1) // 2)
        cells = [_len(r[i]) for r in b["rows"] if i < len(r)]
        typical = sorted(cells)[len(cells) * 3 // 4] if cells else 0
        weights.append(max(header_need + 3, min(typical, 45), 6))
    total = sum(weights)
    return [width * w / total for w in weights]


def _block(b, st, width):
    if b["type"] == "kpis":
        cells = []
        for label, value, tone in b["items"]:
            v = _text(value)
            if tone:
                v = f"<font color='{TONES[tone].hexval()}'>{v}</font>"
            cells.append([Paragraph(v, st["kpi_v"]), Paragraph(_text(label), st["kpi_l"])])
        n = len(cells) or 1
        t = Table([cells], colWidths=[width / n] * n)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
            ("LINEAFTER", (0, 0), (-2, -1), 3, colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return [t, Spacer(1, 4)]
    if b["type"] == "paragraph":
        label = f"<font name='{st['bold']}'>{_text(b['label'])}:</font> " if b.get("label") else ""
        return [Paragraph(label + _text(b["text"]), st["base"]), Spacer(1, 4)]

    if not b["rows"] and not b.get("empty"):
        return []
    out = []
    if b.get("title"):
        out.append(Paragraph(_text(b["title"]), st["h3"]))
    data = [[Paragraph(_text(h), st["th"]) for h in b["headers"]]]
    if b["rows"]:
        data += [[_cell(c, st) for c in r] for r in b["rows"]]
    else:
        data.append([Paragraph(_text(b["empty"]), st["cell"])] + [""] * (len(b["headers"]) - 1))
    t = Table(data, colWidths=_col_widths(b, width), repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if not b["rows"]:
        style.append(("SPAN", (0, 1), (-1, 1)))
    t.setStyle(TableStyle(style))
    out.append(t)
    if b.get("more"):
        out.append(Paragraph(_("… e altri %(n)s") % {"n": b["more"]}, st["note"]))
    out.append(Spacer(1, 4))
    return out


def render_pdf(review) -> bytes:
    doc_model = build_report(review)
    st = _styles()
    buf = io.BytesIO()
    margin = 16 * mm
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=18 * mm,
        title=f"Riesame di Direzione — {review.title}", author="GRC",
    )
    width = A4[0] - 2 * margin
    story = [
        Paragraph(_text(doc_model["title"]), st["h1"]),
        Paragraph(_text(doc_model["subtitle"]), st["sub"]),
    ]
    meta = Table(
        [[Paragraph(_text(k), st["note"]), Paragraph(_text(v), st["base"])] for k, v in doc_model["meta"]],
        colWidths=[35 * mm, width - 35 * mm],
    )
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.append(meta)

    if doc_model["summary"]:
        box = Table([[Paragraph(_text(doc_model["summary"]["text"]), st["base"])]], colWidths=[width])
        box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story += [Paragraph(_("Sintesi executive"), st["h2"]), box, Spacer(1, 3),
                  Paragraph(_text(doc_model["summary"]["note"]), st["note"])]

    if doc_model["alerts"]:
        story.append(Paragraph(_("Punti di attenzione"), st["h2"]))
        story += [Paragraph(f"<font color='{TONES['red'].hexval()}'>•</font> {_text(a)}", st["base"])
                  for a in doc_model["alerts"]]

    for section in doc_model["sections"]:
        flow = []
        for b in section["blocks"]:
            flow += _block(b, st, width)
        heading = Paragraph(_text(section["heading"]), st["h2"])
        # il titolo non resta orfano in fondo alla pagina
        story.append(KeepTogether([heading] + flow[:1]))
        story += flow[1:]

    if doc_model["approval"]:
        a = doc_model["approval"]
        box = Table([[Paragraph(
            f"<font name='{st['bold']}' color='{TONES['green'].hexval()}'>{_text(_('RIESAME APPROVATO'))}</font><br/>"
            f"{_text(_('Approvato da'))}: {_text(a['by'])}<br/>"
            f"{_text(_('Data'))}: {_text(a['at'])}<br/>"
            f"{_text(_('Note'))}: {_text(a['note'])}", st["base"])]],
            colWidths=[width])
        box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, TONES["green"]),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [Spacer(1, 10), box]

    footer = doc_model["footer"]
    regular = st["base"].fontName

    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont(regular, 7)
        canvas.setFillColor(GREY)
        canvas.drawString(margin, 10 * mm, footer)
        canvas.drawRightString(A4[0] - margin, 10 * mm, f"{doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
