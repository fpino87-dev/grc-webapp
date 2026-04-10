"""
Export engine per documenti di compliance.
Genera SOA ISO 27001, VDA ISA TISAX, Compliance Matrix NIS2
dallo stesso dato sorgente: ControlInstance.

Tutti i formati restituiscono HTML stampabile/scaricabile.
"""

import base64
import datetime
import re

from django.core.files.storage import default_storage
from django.utils import timezone


def _isa_sort_key(external_id: str) -> tuple:
    """
    Chiave di ordinamento naturale per external_id in formato ISA.
    Esempi: 'ISA-1.2.1' < 'ISA-1.10.1' < 'ISA-1.10.1-VH' < 'ISA-8.1.1'
    Gestisce correttamente le versioni numeriche (non lessicografiche) e
    il suffisso '-VH' che posiziona L3 dopo il corrispondente controllo L2.
    """
    raw = external_id
    # Rimuovi prefisso alfanumerico iniziale (es. "ISA-")
    m = re.match(r'^[A-Za-z]+-', raw)
    if m:
        raw = raw[m.end():]
    # Rimuovi suffisso non-numerico finale (es. "-VH") e marca come post-base
    suffix = 0
    tail = re.search(r'-[A-Za-z]+$', raw)
    if tail:
        raw = raw[: tail.start()]
        suffix = 1
    nums = tuple(int(x) for x in raw.split(".") if x.isdigit())
    return nums + (suffix,)


def generate_export(framework_code: str, plant_id,
                    export_format: str, user) -> str:
    """
    Entry point principale.

    framework_code: "ISO27001" | "TISAX_L2" | "TISAX_L3" | "TISAX_PROTO" | "NIS2"
    export_format:  "soa" | "vda_isa" | "compliance_matrix"
    Restituisce: stringa HTML pronta per download/stampa
    """
    from apps.controls.models import Framework, ControlInstance
    from apps.plants.models import Plant

    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
    fw = Framework.objects.filter(code=framework_code).first()

    if not fw:
        raise ValueError(
            f"Framework '{framework_code}' non trovato nel database. "
            f"Eseguire: python manage.py load_frameworks"
        )

    # N.B. export engine può essere usato con translation.override(lang)

    def _fetch_instances(framework_obj):
        return ControlInstance.objects.filter(
            plant_id=plant_id,
            control__framework=framework_obj,
            deleted_at__isnull=True,
        ).select_related(
            "control__domain", "control__framework",
            "owner", "soa_approved_by",
            "na_approved_by",
        ).prefetch_related("evidences", "documents").order_by(
            "control__domain__order", "control__external_id"
        )

    # Plant opzionale — se None ritorna queryset vuoto
    if plant_id:
        instances = _fetch_instances(fw)
    else:
        instances = ControlInstance.objects.none()

    if export_format == "soa":
        return _generate_soa(fw, plant, instances, user)
    elif export_format == "vda_isa":
        # TISAX L3 include tutti i controlli L2 + L3
        if framework_code == "TISAX_L3" and plant_id:
            fw_l2 = Framework.objects.filter(code="TISAX_L2").first()
            if fw_l2:
                instances_l2 = _fetch_instances(fw_l2)
                from itertools import chain
                # Sort numerico: "ISA-1.2.1" < "ISA-1.10.1" < "ISA-1.10.1-VH"
                combined = sorted(
                    chain(instances_l2, instances),
                    key=lambda inst: _isa_sort_key(inst.control.external_id),
                )
                return _generate_vda_isa(fw, plant, combined, user)
        # TISAX_PROTO (cap. 8): export VDA ISA autonomo
        return _generate_vda_isa(fw, plant, instances, user)
    elif export_format == "compliance_matrix":
        return _generate_compliance_matrix(fw, plant, instances, user)
    else:
        raise ValueError(
            f"Formato '{export_format}' non supportato. "
            f"Usa: soa, vda_isa, compliance_matrix"
        )


def _get_logo_src_for_plant(plant) -> str | None:
    """
    Restituisce un data URI del logo del plant, se configurato e presente nello storage.
    Usa default_storage partendo da logo_url (tipicamente /media/...).
    """
    if plant is None or not getattr(plant, "logo_url", None):
        return None
    logo_url = plant.logo_url.strip()
    if not logo_url:
        return None

    # Deriva lo storage_path da logo_url (es. /media/plant-logos/...)
    storage_path = logo_url
    if "/media/" in logo_url:
        storage_path = logo_url.split("/media/", 1)[1]
    storage_path = storage_path.lstrip("/")
    if not storage_path or not default_storage.exists(storage_path):
        return None

    with default_storage.open(storage_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _base_html(title: str, content: str, plant_name: str,
               fw_name: str, user_name: str, logo_src: str | None = None) -> str:
    """Template HTML base condiviso da tutti i formati."""
    from django.utils import translation
    lang = translation.get_language() or "it"
    now = timezone.now().strftime("%d/%m/%Y %H:%M")
    logo_img = ""
    if logo_src:
        logo_img = (
            f'<div style="text-align:right;margin-bottom:10px;">'
            f'<img src="{logo_src}" alt="Logo" '
            f'style="max-height:40px;max-width:160px;object-fit:contain;"/>'
            f"</div>"
        )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 10px;
            color: #1f2937; margin: 20px; }}
    h1   {{ font-size: 16px; color: #1e40af;
            border-bottom: 2px solid #1e40af; padding-bottom: 6px; }}
    h2   {{ font-size: 12px; color: #1e40af; margin-top: 18px;
            border-left: 3px solid #1e40af; padding-left: 6px; }}
    table {{ width: 100%; border-collapse: collapse;
             margin: 10px 0; font-size: 9px; }}
    th    {{ background: #1e40af; color: white;
             padding: 5px 6px; text-align: left; }}
    td    {{ padding: 4px 6px; border-bottom: 1px solid #e5e7eb;
             vertical-align: top; }}
    tr:nth-child(even) {{ background: #f9fafb; }}
    .badge-green  {{ background:#dcfce7; color:#166534;
                     padding:1px 5px; border-radius:3px; }}
    .badge-yellow {{ background:#fef9c3; color:#854d0e;
                     padding:1px 5px; border-radius:3px; }}
    .badge-red    {{ background:#fee2e2; color:#991b1b;
                     padding:1px 5px; border-radius:3px; }}
    .badge-gray   {{ background:#f3f4f6; color:#374151;
                     padding:1px 5px; border-radius:3px; }}
    .meta {{ display:grid; grid-template-columns:1fr 1fr;
             gap:6px; margin:10px 0; font-size:9px; }}
    .meta-item {{ background:#f0f4ff; padding:6px;
                  border-radius:4px; }}
    .meta-label {{ color:#6b7280; font-size:8px; }}
    .meta-value {{ font-weight:bold; }}
    .summary {{ display:grid; grid-template-columns:repeat(5,1fr);
                gap:8px; margin:12px 0; }}
    .summary-box {{ text-align:center; padding:8px;
                    border-radius:4px; }}
    .summary-num {{ font-size:18px; font-weight:bold; }}
    .summary-lbl {{ font-size:8px; color:#6b7280; }}
    .footer {{ margin-top:30px; border-top:1px solid #e5e7eb;
               padding-top:8px; font-size:8px; color:#9ca3af;
               text-align:center; }}
    .signature {{ border:1px solid #d1d5db; padding:10px;
                  margin-top:20px; border-radius:4px; }}
    @media print {{ body {{ margin:0; }} }}
  </style>
</head>
<body>
{logo_img}
{content}
<div class="footer">
  Generato da GRC System il {now} — Utente: {user_name} —
  Sito: {plant_name} — Framework: {fw_name} — RISERVATO
</div>
</body>
</html>"""


def _status_badge(status: str) -> str:
    from django.utils.translation import gettext as _
    badges = {
        "compliant":    f'<span class="badge-green">{_("Compliant")}</span>',
        "parziale":     f'<span class="badge-yellow">{_("Parziale")}</span>',
        "gap":          f'<span class="badge-red">{_("Gap")}</span>',
        "na":           f'<span class="badge-gray">{_("N/A")}</span>',
        "non_valutato": f'<span class="badge-gray">{_("Non valutato")}</span>',
    }
    return badges.get(status, status)


def _applicability_badge(applicability: str) -> str:
    from django.utils.translation import gettext as _
    badges = {
        "applicabile":    f'<span class="badge-green">{_("Applicabile")}</span>',
        "escluso":        f'<span class="badge-red">{_("Escluso")}</span>',
        "non_pertinente": f'<span class="badge-gray">{_("Non pertinente")}</span>',
    }
    return badges.get(applicability, applicability)


def _generate_soa(fw, plant, instances, user) -> str:
    """Statement of Applicability — ISO 27001 clausola 6.1.3"""
    from django.utils import translation
    lang = translation.get_language() or "it"
    total = instances.count()
    by_app = {}
    by_status = {}
    for inst in instances:
        app = inst.applicability
        by_app[app] = by_app.get(app, 0) + 1
        by_status[inst.status] = by_status.get(inst.status, 0) + 1

    compliant = by_status.get("compliant", 0)
    excluded = by_app.get("escluso", 0)
    pct = round(compliant / (total - excluded) * 100, 1) \
        if (total - excluded) > 0 else 0

    domains = {}
    for inst in instances:
        domain = inst.control.domain.get_name(lang) if inst.control.domain else "Altro"
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(inst)

    rows_html = ""
    for domain, insts in domains.items():
        rows_html += f"""
        <tr style="background:#dbeafe">
          <td colspan="8"><strong>{domain}</strong></td>
        </tr>"""
        for inst in insts:
            owner_name = ""
            if inst.owner:
                owner_name = (
                    f"{inst.owner.first_name} {inst.owner.last_name}".strip()
                    or inst.owner.email
                )
            ev_count = inst.evidences.filter(
                valid_until__gte=timezone.now().date()
            ).count()
            last_eval = inst.last_evaluated_at.strftime("%d/%m/%Y") \
                if inst.last_evaluated_at else "—"
            justif = (inst.exclusion_justification or
                      inst.na_justification or "")[:80]
            rows_html += f"""
        <tr>
          <td><strong>{inst.control.external_id}</strong></td>
          <td>{inst.control.get_title(lang)[:60]}</td>
          <td>{_applicability_badge(inst.applicability)}</td>
          <td>{_status_badge(inst.status)}</td>
          <td>{justif}</td>
          <td>{owner_name}</td>
          <td>{last_eval}</td>
          <td>{ev_count} evidenze</td>
        </tr>"""

    plant_name = plant.name if plant else "Organizzazione"
    user_name = (f"{user.first_name} {user.last_name}".strip() or user.email)

    content = f"""
<h1>Statement of Applicability (SOA)</h1>
<p style="color:#6b7280;font-size:9px">
  ISO/IEC 27001:2022 — Clausola 6.1.3 — Annex A Controls
</p>

<div class="meta">
  <div class="meta-item">
    <div class="meta-label">Organizzazione / Sito</div>
    <div class="meta-value">{plant_name}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Framework</div>
    <div class="meta-value">{fw.name} v{fw.version}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Data generazione</div>
    <div class="meta-value">{timezone.now().strftime("%d/%m/%Y")}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Generato da</div>
    <div class="meta-value">{user_name}</div>
  </div>
</div>

<div class="summary">
  <div class="summary-box" style="background:#f0f4ff">
    <div class="summary-num">{total}</div>
    <div class="summary-lbl">Totale controlli</div>
  </div>
  <div class="summary-box" style="background:#dcfce7">
    <div class="summary-num">{compliant}</div>
    <div class="summary-lbl">Compliant</div>
  </div>
  <div class="summary-box" style="background:#fee2e2">
    <div class="summary-num">{by_status.get("gap", 0)}</div>
    <div class="summary-lbl">Gap</div>
  </div>
  <div class="summary-box" style="background:#f3f4f6">
    <div class="summary-num">{excluded}</div>
    <div class="summary-lbl">Esclusi</div>
  </div>
  <div class="summary-box" style="background:#fef9c3">
    <div class="summary-num">{pct}%</div>
    <div class="summary-lbl">% Compliant (applicabili)</div>
  </div>
</div>

<table>
  <tr>
    <th>ID Controllo</th>
    <th>Titolo</th>
    <th>Applicabilit&#224;</th>
    <th>Stato</th>
    <th>Giustificazione esclusione</th>
    <th>Owner</th>
    <th>Ultima valutazione</th>
    <th>Evidenze</th>
  </tr>
  {rows_html}
</table>

<div class="signature">
  <strong>Approvazione SOA</strong><br><br>
  Firma CISO / Information Security Manager: ________________________<br><br>
  Firma Management: ________________________<br><br>
  Data: __________________ &nbsp;&nbsp;
  Versione documento: 1.0
</div>"""

    # Clausola 8.1 — change management evidence
    change_section = _generate_soa_change_section(plant)
    content += change_section

    logo_src = _get_logo_src_for_plant(plant)
    return _base_html(
        f"SOA — {plant_name}",
        content, plant_name, fw.name, user_name, logo_src
    )


def _generate_soa_change_section(plant) -> str:
    """Sezione clausola 8.1 — asset con change recenti (ultimi 90gg)."""
    from apps.assets.models import Asset

    since = timezone.now().date() - datetime.timedelta(days=90)
    qs_args = dict(last_change_date__gte=since, deleted_at__isnull=True)
    if plant is not None:
        qs_args["plant"] = plant
    recent_changes = Asset.objects.filter(**qs_args).order_by("-last_change_date")

    if recent_changes.exists():
        rows = ""
        for asset in recent_changes:
            rivalutato = (
                '<span class="badge-green">Sì</span>'
                if not asset.needs_revaluation
                else '<span class="badge-red">In attesa</span>'
            )
            portal_link = (
                f'<a href="{asset.change_portal_url}" style="color:#1e40af">'
                f'{asset.last_change_ref}</a>'
                if asset.change_portal_url
                else asset.last_change_ref or "—"
            )
            rows += f"""
        <tr>
          <td>{asset.name}</td>
          <td>{portal_link}</td>
          <td>{asset.last_change_date.strftime("%d/%m/%Y") if asset.last_change_date else "—"}</td>
          <td>{(asset.last_change_desc or "")[:80]}</td>
          <td>{rivalutato}</td>
        </tr>"""
        table_html = f"""
<table>
  <tr>
    <th>Asset</th>
    <th>Change ref</th>
    <th>Data</th>
    <th>Descrizione</th>
    <th>Rivalutato?</th>
  </tr>
  {rows}
</table>"""
    else:
        table_html = "<p style='font-size:9px;color:#6b7280'>Nessun change registrato negli ultimi 90 giorni.</p>"

    return f"""
<h2>Nota sulla gestione delle modifiche (Clausola 8.1)</h2>
<p style="font-size:10px">
  La gestione delle modifiche ai sistemi informativi è gestita tramite il sistema
  di ticketing aziendale. Il GRC System integra i riferimenti ai change ticket
  direttamente sugli asset, generando automaticamente alert di rivalutazione per
  i controlli e i risk assessment impattati. La presente nota costituisce evidenza
  del processo di controllo delle modifiche ai sensi della clausola 8.1 di
  ISO/IEC 27001:2022.
</p>
<p style="font-size:9px;font-weight:bold">Asset con change recenti (ultimi 90 giorni):</p>
{table_html}"""


def _generate_vda_isa(fw, plant, instances, user) -> str:
    """VDA ISA Export — TISAX, maturity level 0-5"""
    plant_name = plant.name if plant else "Organizzazione"
    user_name = (f"{user.first_name} {user.last_name}".strip() or user.email)

    MATURITY_LABELS = {
        0: "0 — Non implementato",
        1: "1 — Ad-hoc / Informale",
        2: "2 — Pianificato",
        3: "3 — Definito e documentato",
        4: "4 — Gestito e misurato",
        5: "5 — Ottimizzato",
    }
    MATURITY_COLORS = {
        0: "#fee2e2", 1: "#fecaca", 2: "#fef9c3",
        3: "#fef3c7", 4: "#dcfce7", 5: "#bbf7d0",
    }

    rows_html = ""
    total_ml = 0
    count_with = 0

    for inst in instances:
        ml = inst.calc_maturity_level
        ml_label = MATURITY_LABELS.get(ml, str(ml))
        ml_color = MATURITY_COLORS.get(ml, "#f3f4f6")
        level_tag = inst.control.level or "L2"
        owner_name = ""
        if inst.owner:
            owner_name = (
                f"{inst.owner.first_name} {inst.owner.last_name}".strip()
                or inst.owner.email
            )
        justif = (inst.na_justification or
                  inst.exclusion_justification or "")[:100]
        if inst.status != "na":
            total_ml += ml
            count_with += 1

        rows_html += f"""
        <tr>
          <td><strong>{inst.control.external_id}</strong></td>
          <td>{level_tag}</td>
          <td>{inst.control.get_title("en")[:70]}</td>
          <td style="background:{ml_color};font-weight:bold">{ml}</td>
          <td style="background:{ml_color}">{ml_label}</td>
          <td>{_status_badge(inst.status)}</td>
          <td>{owner_name}</td>
          <td>{justif}</td>
        </tr>"""

    avg_ml = round(total_ml / count_with, 1) if count_with > 0 else 0

    content = f"""
<h1>VDA ISA Assessment Export</h1>
<p style="color:#6b7280;font-size:9px">
  TISAX — VDA Information Security Assessment —
  {fw.name} v{fw.version}
</p>

<div class="meta">
  <div class="meta-item">
    <div class="meta-label">Sito</div>
    <div class="meta-value">{plant_name}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Framework / Livello</div>
    <div class="meta-value">{fw.name}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Maturity medio</div>
    <div class="meta-value">{avg_ml} / 5</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Data assessment</div>
    <div class="meta-value">{timezone.now().strftime("%d/%m/%Y")}</div>
  </div>
</div>

<table>
  <tr>
    <th>ID</th>
    <th>Livello</th>
    <th>Requisito</th>
    <th>ML</th>
    <th>Maturity Level</th>
    <th>Stato GRC</th>
    <th>Owner</th>
    <th>Note / Justification</th>
  </tr>
  {rows_html}
</table>

<div class="signature">
  <strong>Dichiarazione di conformit&#224; TISAX</strong><br><br>
  Il presente documento &#232; stato prodotto dal sistema GRC interno
  sulla base delle valutazioni dei controlli effettuate dai
  Control Owner certificati.<br><br>
  Firma Information Security Manager: ________________________<br>
  Data: __________________
</div>"""

    logo_src = _get_logo_src_for_plant(plant)
    return _base_html(
        f"VDA ISA — {plant_name}",
        content, plant_name, fw.name, user_name, logo_src
    )


def _generate_compliance_matrix(fw, plant, instances, user) -> str:
    """Compliance Matrix NIS2"""
    from django.utils import translation
    lang = translation.get_language() or "it"
    plant_name = plant.name if plant else "Organizzazione"
    user_name = (f"{user.first_name} {user.last_name}".strip() or user.email)
    nis2_scope = getattr(plant, "nis2_scope", "—") if plant else "—"

    rows_html = ""
    for inst in instances:
        domain = inst.control.domain.get_name(lang) if inst.control.domain else ""
        owner_name = ""
        if inst.owner:
            owner_name = (
                f"{inst.owner.first_name} {inst.owner.last_name}".strip()
                or inst.owner.email
            )
        mappings = inst.control.mappings_from.select_related(
            "target_control__framework"
        ).values(
            "target_control__framework__code",
            "target_control__external_id",
        )[:3]
        mapping_str = ", ".join(
            f"{m['target_control__framework__code']} "
            f"{m['target_control__external_id']}"
            for m in mappings
        ) or "—"

        last_eval = inst.last_evaluated_at.strftime("%d/%m/%Y") \
            if inst.last_evaluated_at else "—"
        note = (inst.last_evaluated_note or "")[:80] if hasattr(inst, "last_evaluated_note") else "—"

        rows_html += f"""
        <tr>
          <td><strong>{inst.control.external_id}</strong></td>
          <td>{domain}</td>
          <td>{inst.control.get_title(lang)[:80]}</td>
          <td>{_status_badge(inst.status)}</td>
          <td>{note}</td>
          <td>{mapping_str}</td>
          <td>{owner_name}</td>
          <td>{last_eval}</td>
        </tr>"""

    total = instances.count()
    compliant = instances.filter(status="compliant").count()
    gap = instances.filter(status="gap").count()
    parziale = instances.filter(status="parziale").count()
    pct = round(compliant / total * 100, 1) if total > 0 else 0

    content = f"""
<h1>NIS2 Compliance Matrix</h1>
<p style="color:#6b7280;font-size:9px">
  Direttiva NIS2 (UE 2022/2555) — Misure di sicurezza adottate
</p>

<div class="meta">
  <div class="meta-item">
    <div class="meta-label">Organizzazione / Sito</div>
    <div class="meta-value">{plant_name}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Ambito NIS2</div>
    <div class="meta-value">{nis2_scope}</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Compliance NIS2</div>
    <div class="meta-value">{pct}%</div>
  </div>
  <div class="meta-item">
    <div class="meta-label">Data</div>
    <div class="meta-value">{timezone.now().strftime("%d/%m/%Y")}</div>
  </div>
</div>

<div class="summary">
  <div class="summary-box" style="background:#f0f4ff">
    <div class="summary-num">{total}</div>
    <div class="summary-lbl">Requisiti totali</div>
  </div>
  <div class="summary-box" style="background:#dcfce7">
    <div class="summary-num">{compliant}</div>
    <div class="summary-lbl">Soddisfatti</div>
  </div>
  <div class="summary-box" style="background:#fee2e2">
    <div class="summary-num">{gap}</div>
    <div class="summary-lbl">Gap</div>
  </div>
  <div class="summary-box" style="background:#fef9c3">
    <div class="summary-num">{parziale}</div>
    <div class="summary-lbl">Parziali</div>
  </div>
  <div class="summary-box" style="background:#fef9c3">
    <div class="summary-num">{pct}%</div>
    <div class="summary-lbl">% Compliance</div>
  </div>
</div>

<table>
  <tr>
    <th>Requisito</th>
    <th>Area</th>
    <th>Misura / Controllo</th>
    <th>Stato</th>
    <th>Misura adottata</th>
    <th>Mapping ISO/TISAX</th>
    <th>Responsabile</th>
    <th>Ultima verifica</th>
  </tr>
  {rows_html}
</table>

<div class="signature">
  <strong>Dichiarazione NIS2</strong><br><br>
  La presente matrice attesta le misure di sicurezza adottate
  ai sensi dell'Art. 21 della Direttiva NIS2.<br><br>
  Firma CISO: ________________________ &nbsp;&nbsp;
  Firma Legale Rappresentante: ________________________<br>
  Data: __________________
</div>"""

    logo_src = _get_logo_src_for_plant(plant)
    return _base_html(
        f"NIS2 Compliance Matrix — {plant_name}",
        content, plant_name, fw.name, user_name, logo_src
    )
