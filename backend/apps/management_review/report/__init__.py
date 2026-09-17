"""Relazione (verbale) del riesame di direzione: un modello unico (`builder`)
e due renderer, HTML e PDF."""
from .builder import build_report
from .html import render_html
from .pdf import render_pdf

__all__ = ["build_report", "render_html", "render_pdf"]
