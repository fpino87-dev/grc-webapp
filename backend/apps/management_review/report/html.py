"""Renderer HTML della relazione (stampabile/archiviabile)."""
from html import escape

from django.utils.translation import gettext as _

from .builder import build_report

TONES = {"red": "#dc2626", "orange": "#d97706", "green": "#16a34a", "muted": "#6b7280"}

CSS = """
body { font-family: Arial, sans-serif; font-size: 12px; color: #333; max-width: 960px; margin: 40px auto; padding: 0 20px; }
h1 { font-size: 20px; border-bottom: 2px solid #1e40af; padding-bottom: 8px; color: #1e40af; margin-bottom: 2px; }
.subtitle { color: #6b7280; font-size: 11px; margin: 0 0 16px; }
h2 { font-size: 14px; color: #1e40af; margin-top: 28px; border-left: 4px solid #1e40af; padding-left: 8px; }
h3 { font-size: 11px; color: #374151; margin: 14px 0 4px; }
table { width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 11px; }
th { background: #1e40af; color: white; padding: 5px 8px; text-align: left; }
td { padding: 4px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
tr:nth-child(even) td { background: #f9fafb; }
table.meta td { border: none; background: none; padding: 3px 8px 3px 0; }
table.meta td.k { color: #6b7280; width: 140px; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; }
.kpi { background: #f0f4ff; border-radius: 6px; padding: 8px; text-align: center; }
.kpi-value { font-size: 20px; font-weight: bold; color: #1e40af; }
.kpi-label { font-size: 10px; color: #6b7280; margin-top: 2px; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 6px 10px; border-radius: 4px; margin: 4px 0; font-size: 11px; }
.summary { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; white-space: pre-wrap; line-height: 1.5; }
.ai-note { font-size: 10px; color: #6b7280; margin-top: 6px; font-style: italic; }
.para { white-space: pre-wrap; margin: 6px 0; }
.label { font-weight: bold; color: #374151; }
.more { font-size: 10px; color: #6b7280; margin: -6px 0 8px; }
.approval { border: 2px solid #16a34a; padding: 14px; margin-top: 28px; border-radius: 8px; }
.footer { font-size: 10px; color: #9ca3af; text-align: center; margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 8px; }
@media print { body { margin: 0; } h2 { page-break-after: avoid; } }
"""


def _cell(c) -> str:
    if isinstance(c, dict):
        style = []
        if c.get("tone"):
            style.append(f"color:{TONES[c['tone']]}")
        if c.get("bold"):
            style.append("font-weight:bold")
        text = escape(str(c.get("text", "")))
        return f"<span style='{';'.join(style)}'>{text}</span>" if style else text
    return escape(str(c))


def _block(b) -> str:
    if b["type"] == "kpis":
        items = "".join(
            f"<div class='kpi'><div class='kpi-value' style='color:{TONES.get(tone, '#1e40af')}'>{escape(str(v))}</div>"
            f"<div class='kpi-label'>{escape(label)}</div></div>"
            for label, v, tone in b["items"]
        )
        return f"<div class='kpi-grid'>{items}</div>"
    if b["type"] == "paragraph":
        label = f"<span class='label'>{escape(b['label'])}:</span> " if b.get("label") else ""
        return f"<p class='para'>{label}{escape(b['text'])}</p>"
    # table
    if not b["rows"] and not b.get("empty"):
        return ""
    title = f"<h3>{escape(b['title'])}</h3>" if b.get("title") else ""
    head = "".join(f"<th>{escape(h)}</th>" for h in b["headers"])
    if b["rows"]:
        body = "".join("<tr>" + "".join(f"<td>{_cell(c)}</td>" for c in r) + "</tr>" for r in b["rows"])
    else:
        body = f"<tr><td colspan='{len(b['headers'])}'>{escape(b['empty'])}</td></tr>"
    more = (f"<p class='more'>{escape(_('… e altri %(n)s') % {'n': b['more']})}</p>"
            if b.get("more") else "")
    return f"{title}<table><tr>{head}</tr>{body}</table>{more}"


def render_html(review) -> str:
    doc = build_report(review)
    meta = "".join(f"<tr><td class='k'>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in doc["meta"])
    parts = [
        f"<h1>{escape(doc['title'])}</h1><p class='subtitle'>{escape(doc['subtitle'])}</p>",
        f"<table class='meta'>{meta}</table>",
    ]
    if doc["summary"]:
        parts.append(
            f"<h2>{escape(_('Sintesi executive'))}</h2>"
            f"<div class='summary'>{escape(doc['summary']['text'])}</div>"
            f"<p class='ai-note'>{escape(doc['summary']['note'])}</p>"
        )
    if doc["alerts"]:
        parts.append(f"<h2>{escape(_('Punti di attenzione'))}</h2>"
                     + "".join(f"<div class='alert'>⚠️ {escape(str(a))}</div>" for a in doc["alerts"]))
    for section in doc["sections"]:
        parts.append(f"<h2>{escape(section['heading'])}</h2>" + "".join(_block(b) for b in section["blocks"]))
    if doc["approval"]:
        a = doc["approval"]
        parts.append(
            f"<div class='approval'><strong style='color:#16a34a'>✓ {escape(_('RIESAME APPROVATO'))}</strong><br>"
            + "<br>".join(f"{escape(str(k))}: {escape(str(v))}" for k, v in a["lines"])
            + "</div>"
        )
    parts.append(f"<p class='footer'>{escape(doc['footer'])}</p>")
    return (
        "<!DOCTYPE html>\n<html lang=\"it\">\n<head>\n<meta charset=\"UTF-8\">\n"
        f"<title>Riesame di Direzione — {escape(review.title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        + "\n".join(parts) + "\n</body>\n</html>"
    )
