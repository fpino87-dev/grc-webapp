import os as _os
import re as _re

from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ControlInstance
from ..permissions import ControlsReportPermission


# ─── helpers audit package ────────────────────────────────────────────────────

def _sanitize_name(text: str, max_len: int = 60) -> str:
    text = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text or "")
    text = _re.sub(r"\s+", "_", text.strip())
    text = _re.sub(r"_+", "_", text)
    return text[:max_len].rstrip("_")


def _sort_control_key(external_id: str):
    parts = _re.split(r"[.\-]", external_id)
    result = []
    for p in parts:
        try:
            result.append((0, int(p)))
        except ValueError:
            result.append((1, p.upper()))
    return result


def _add_audit_programs(zf, zip_name: str, fw_codes: list[str], plant_id, today) -> None:
    """
    Aggiunge PROGRAMMA_AUDIT/ con un CSV per ogni programma approvato/in_corso
    del plant che copre almeno uno dei framework del pacchetto.
    """
    import io

    from core.csv_safe import safe_writer
    from apps.audit_prep.models import AuditProgram

    qs = AuditProgram.objects.filter(
        deleted_at__isnull=True,
        status__in=("approvato", "in_corso", "completato"),
    ).select_related("plant", "approved_by").prefetch_related("frameworks")
    if plant_id:
        qs = qs.filter(plant_id=plant_id)

    # Filtra per framework rilevanti
    programs = [
        p for p in qs
        if any(f.code in fw_codes for f in p.frameworks.all())
        or (p.framework and p.framework.code in fw_codes)
    ]

    if not programs:
        return

    for prog in programs:
        buf = io.StringIO()
        w = safe_writer(buf)

        # Intestazione programma
        w.writerow(["PROGRAMMA DI AUDIT INTERNO"])
        w.writerow(["Titolo", prog.title])
        w.writerow(["Anno", prog.year])
        w.writerow(["Stato", prog.status])
        w.writerow(["Copertura", prog.coverage_type])
        w.writerow(["Approvato da", prog.approved_by.get_full_name() if prog.approved_by else "—"])
        w.writerow(["Approvato il", prog.approved_at.strftime("%Y-%m-%d") if prog.approved_at else "—"])
        w.writerow(["Generato il", today.isoformat()])
        w.writerow([])

        if prog.objectives:
            w.writerow(["OBIETTIVI"])
            w.writerow([prog.objectives])
            w.writerow([])

        if prog.scope:
            w.writerow(["PERIMETRO / SCOPE"])
            w.writerow([prog.scope])
            w.writerow([])

        if prog.methodology:
            w.writerow(["METODOLOGIA"])
            w.writerow([prog.methodology])
            w.writerow([])

        # Audit pianificati
        audits = prog.planned_audits or []
        if audits:
            w.writerow(["AUDIT PIANIFICATI"])
            w.writerow(["Data pianificata", "Titolo", "Auditor", "Perimetro", "Stato", "Note"])
            for a in sorted(audits, key=lambda x: x.get("planned_date", "")):
                w.writerow([
                    a.get("planned_date", "—"),
                    a.get("title", "—"),
                    a.get("auditor", "—"),
                    a.get("scope", "—"),
                    a.get("status", "—"),
                    a.get("notes", ""),
                ])

        safe_title = _sanitize_name(prog.title, 50)
        fname = f"{prog.year}_{safe_title}.csv"
        zf.writestr(
            f"{zip_name}/PROGRAMMA_AUDIT/{fname}",
            buf.getvalue().encode("utf-8-sig"),
        )


def _add_management_reviews(zf, zip_name: str, plant_id, default_storage) -> None:
    """
    Aggiunge REVISIONI_DIREZIONE/ con:
    - RIEPILOGO.csv  — tutte le revisioni completate/approvate
    - file documento (verbale) per ogni revisione che ha document_id impostato
    """
    import io

    from core.csv_safe import safe_writer
    from apps.management_review.models import ManagementReview
    from apps.documents.models import Document

    from django.db.models import Count, Q

    # Solo i riesami completi §9.3: le sedute mirate non sono il riesame periodico.
    qs = ManagementReview.objects.filter(
        deleted_at__isnull=True,
        status="completato",
        kind="completo",
    ).select_related("approved_by", "approved_member", "governing_body").prefetch_related(
        "participants"
    ).annotate(
        n_actions=Count("actions", filter=Q(actions__deleted_at__isnull=True))
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)

    reviews = list(qs.order_by("-review_date"))
    if not reviews:
        return

    # Riepilogo CSV
    buf = io.StringIO()
    w = safe_writer(buf)
    w.writerow(["Data", "Titolo", "Organo", "Presidente", "Stato approvazione", "Forma approvazione",
                "Approvato da", "Approvato il", "Prossima revisione",
                "N. decisioni", "Verbale allegato"])
    for r in reviews:
        has_doc = bool(r.document_id)
        w.writerow([
            r.review_date.isoformat(),
            r.title,
            r.governing_body.name if r.governing_body_id else "—",
            next((p.full_name for p in r.participants.all() if p.is_chair), "—"),
            r.approval_status,
            {"in_app": "In app", "delibera": f"Delibera {r.approval_resolution_ref}"}.get(r.approval_mode, "—"),
            (r.approved_member.full_name if r.approved_member_id
             else r.approved_by.get_full_name() if r.approved_by else "—"),
            r.approved_at.strftime("%Y-%m-%d") if r.approved_at else "—",
            r.next_review_date.isoformat() if r.next_review_date else "—",
            r.n_actions,
            "Sì" if has_doc else "No",
        ])
    zf.writestr(
        f"{zip_name}/REVISIONI_DIREZIONE/RIEPILOGO.csv",
        buf.getvalue().encode("utf-8-sig"),
    )

    # Verbali (file documento allegato)
    for r in reviews:
        if not r.document_id:
            continue
        try:
            doc = Document.objects.get(pk=r.document_id, deleted_at__isnull=True)
            version = doc.versions.order_by("-version_number").first()
            if not version or not version.storage_path:
                continue
            if not default_storage.exists(version.storage_path):
                continue
            content = default_storage.open(version.storage_path, "rb").read()
            _, ext = _os.path.splitext(version.file_name or version.storage_path)
            safe_title = _sanitize_name(r.title, 50)
            fname = f"{r.review_date.isoformat()}_{safe_title}{ext}"
            zf.writestr(
                f"{zip_name}/REVISIONI_DIREZIONE/{fname}",
                content,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "audit-package: verbale revisione %s saltato: %s", getattr(r, "pk", "?"), exc,
            )


def _add_external_audit_reports(zf, zip_name: str, plant_id, default_storage) -> None:
    """
    Aggiunge AUDIT_ESTERNI/ con:
    - RIEPILOGO.csv — audit di seconda e terza parte e audit interni affidati a
      un consulente esterno (tipo, committente, ente,
      data, n. finding, presenza del rapporto)
    - il rapporto ufficiale allegato a ciascun audit (se presente)
    """
    import io
    import logging
    import os as _os

    from django.db.models import Count, Q

    from core.csv_safe import safe_writer
    from apps.audit_prep.models import AuditPrep

    qs = (
        AuditPrep.objects.filter(
            Q(audit_type__in=("seconda_parte", "terza_parte"))
            # audit interno condotto da un consulente esterno: anche lui ha un rapporto
            | Q(audit_type="interno", external_consultant=True)
        )
        .exclude(status="archiviato")
        .select_related("report_evidence")
        .annotate(n_findings=Count("findings", filter=Q(findings__deleted_at__isnull=True)))
        .order_by("-audit_date")
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    preps = list(qs)
    if not preps:
        return

    type_label = dict(AuditPrep.AUDIT_TYPE_CHOICES)
    buf = io.StringIO()
    w = safe_writer(buf)
    w.writerow(["Data", "Titolo", "Tipo", "Committente", "Ente / auditor", "Stato", "Finding", "Rapporto"])
    for p in preps:
        w.writerow([
            p.audit_date.isoformat() if p.audit_date else "—",
            p.title,
            type_label.get(p.audit_type, p.audit_type)
            + (" — consulente esterno" if p.external_consultant else ""),
            p.requesting_party or "—",
            p.auditor_name or "—",
            p.status,
            p.n_findings,
            "Sì" if p.report_evidence_id else "No",
        ])
    zf.writestr(f"{zip_name}/AUDIT_ESTERNI/RIEPILOGO.csv", buf.getvalue().encode("utf-8-sig"))

    for p in preps:
        ev = p.report_evidence
        if not ev or ev.deleted_at or not ev.file_path:
            continue
        try:
            if not default_storage.exists(ev.file_path):
                continue
            content = default_storage.open(ev.file_path, "rb").read()
            _, ext = _os.path.splitext(ev.file_path)
            date = p.audit_date.isoformat() if p.audit_date else "senza-data"
            fname = f"{date}_{_sanitize_name(p.title, 50)}{ext}"
            zf.writestr(f"{zip_name}/AUDIT_ESTERNI/{fname}", content)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "audit-package: rapporto audit %s saltato: %s", p.pk, exc,
            )


def _add_management_review_reports(zf, zip_name: str, plant_id) -> None:
    """Verbali PDF generati dal sistema per i riesami approvati."""
    import logging

    from apps.management_review.models import ManagementReview
    from apps.management_review.report import render_pdf

    qs = (
        ManagementReview.objects.filter(
            approval_status="approvato", snapshot_generated_at__isnull=False, kind="completo",
        )
        .select_related("plant", "governing_body", "approved_by", "approved_member")
        .prefetch_related("participants", "agenda_items", "actions__owner", "actions__task", "actions__pdca_cycle")
    )
    if plant_id:
        qs = qs.filter(plant_id=plant_id)
    for r in qs:
        try:
            fname = f"{r.review_date.isoformat()}_{_sanitize_name(r.title, 50)}_verbale.pdf"
            zf.writestr(f"{zip_name}/REVISIONI_DIREZIONE/{fname}", render_pdf(r))
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "audit-package: verbale PDF del riesame %s non generato: %s", r.pk, exc,
            )


def _add_risk_register(zf, zip_name: str, plant_id) -> None:
    from apps.risk.services import generate_risk_excel
    try:
        excel_bytes = generate_risk_excel(plant_id=plant_id, include_draft=False)
        zf.writestr(f"{zip_name}/RISK_REGISTER/risk_register.xlsx", excel_bytes)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "audit-package: risk register non incluso nello ZIP: %s", exc,
        )


class AuditPackageView(APIView):
    """
    GET /api/v1/controls/audit-package/?framework=TISAX&plant=<uuid>

    Genera uno ZIP pronto per l'auditor:
      - Una cartella per ogni controllo (es. ISA-1.1.1/)
        con sotto-cartelle documenti/ ed evidenze/
      - INDICE.csv   — panoramica di tutti i controlli
      - MANCANZE.txt — solo controlli in trattamento con gap o evidenze scadute
                       (i controlli N/A sono esclusi: fuori trattamento)

    Framework supportati: TISAX (= L2+L3 unificati), TISAX_L2, TISAX_L3,
                          ISO27001, NIS2, ACN_NIS2.
    """

    permission_classes = [ControlsReportPermission]

    def get(self, request):
        import io
        import zipfile
        from core.csv_safe import safe_writer
        from django.core.files.storage import default_storage
        from django.http import HttpResponse
        from django.utils import timezone
        from core.audit import log_action
        from apps.plants.models import Plant
        from ..services import check_evidence_requirements

        framework_param = request.query_params.get("framework", "").strip()
        plant_id = request.query_params.get("plant", "").strip() or None

        if not framework_param:
            return Response({"error": "Parametro 'framework' obbligatorio."}, status=400)

        # TISAX unificato: L2 e L3 vengono trattati come un unico framework
        if framework_param in ("TISAX", "TISAX_L2", "TISAX_L3"):
            fw_codes = ["TISAX_L2", "TISAX_L3"]
            zip_fw_label = "TISAX"
        else:
            fw_codes = [framework_param]
            zip_fw_label = framework_param

        # Il pacchetto audit contiene documenti ed evidenze del sito: richiede
        # accesso al plant; senza plant copre TUTTI i siti → solo scope org
        # (security review 2026-06-12).
        from core.scoping import get_user_plant_ids, user_can_access_plant
        if plant_id:
            if not user_can_access_plant(request.user, plant_id):
                return Response({"error": "Accesso negato per questo sito."}, status=403)
        elif get_user_plant_ids(request.user) is not None:
            return Response({"error": "Accesso negato: pacchetto aggregato riservato allo scope organizzazione."}, status=403)

        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        plant_code = plant.code if plant else "all"

        # Istanze controllo con documenti ed evidenze
        qs = (
            ControlInstance.objects
            .filter(control__framework__code__in=fw_codes, deleted_at__isnull=True)
            .select_related("control", "control__framework", "plant")
            .prefetch_related(
                "documents__versions",
                "evidences",
            )
        )
        if plant_id:
            qs = qs.filter(plant_id=plant_id)

        # Raggruppa per external_id (merge L2+L3 sullo stesso controllo)
        STATUS_RANK = {"gap": 0, "non_valutato": 1, "parziale": 2, "compliant": 3, "na": 99}
        merged: dict[str, dict] = {}
        for inst in qs:
            ext_id = inst.control.external_id
            if ext_id not in merged:
                merged[ext_id] = {
                    "external_id": ext_id,
                    "title": inst.control.get_title("it"),
                    "status": inst.status,
                    "applicability": getattr(inst, "applicability", "applicabile"),
                    "last_evaluated_at": inst.last_evaluated_at,
                    "instances": [],
                    "doc_ids": set(),
                    "ev_ids": set(),
                    "doc_objects": [],
                    "ev_objects": [],
                }
            entry = merged[ext_id]
            entry["instances"].append(inst)
            # Status: prendi il "peggiore" tra tutte le istanze
            if STATUS_RANK.get(inst.status, 0) < STATUS_RANK.get(entry["status"], 99):
                entry["status"] = inst.status
            # last_evaluated_at: prendi il più recente
            if inst.last_evaluated_at and (
                not entry["last_evaluated_at"]
                or inst.last_evaluated_at > entry["last_evaluated_at"]
            ):
                entry["last_evaluated_at"] = inst.last_evaluated_at
            # Documenti (unione)
            for doc in inst.documents.filter(deleted_at__isnull=True):
                if doc.id not in entry["doc_ids"]:
                    entry["doc_ids"].add(doc.id)
                    entry["doc_objects"].append(doc)
            # Evidenze (unione)
            for ev in inst.evidences.filter(deleted_at__isnull=True):
                if ev.id not in entry["ev_ids"]:
                    entry["ev_ids"].add(ev.id)
                    entry["ev_objects"].append(ev)

        controls_list = sorted(merged.values(), key=lambda x: _sort_control_key(x["external_id"]))

        today = timezone.localdate()
        zip_name = f"audit_{zip_fw_label}_{plant_code}_{today.isoformat()}"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:

            # ── INDICE.csv ────────────────────────────────────────────────────
            indice_buf = io.StringIO()
            w = safe_writer(indice_buf)
            w.writerow(["ID Controllo", "Titolo", "Framework", "Stato",
                        "N. Documenti", "N. Evidenze", "Ultima Valutazione"])
            for ctrl in controls_list:
                w.writerow([
                    ctrl["external_id"],
                    ctrl["title"],
                    zip_fw_label,
                    ctrl["status"],
                    len(ctrl["doc_objects"]),
                    len(ctrl["ev_objects"]),
                    ctrl["last_evaluated_at"].strftime("%Y-%m-%d")
                    if ctrl["last_evaluated_at"] else "—",
                ])
            zf.writestr(
                f"{zip_name}/INDICE.csv",
                indice_buf.getvalue().encode("utf-8-sig"),  # BOM per Excel
            )

            # ── MANCANZE.txt ──────────────────────────────────────────────────
            mancanze: list[str] = []
            for ctrl in controls_list:
                # N/A e "escluso/non_pertinente" = fuori trattamento, non sono mancanze
                if ctrl["status"] == "na":
                    continue
                if ctrl["applicability"] in ("escluso", "non_pertinente"):
                    continue
                gap_lines: list[str] = []
                for inst in ctrl["instances"]:
                    req = check_evidence_requirements(inst)
                    for md in req["missing_documents"]:
                        desc = md.get("description") or md.get("type", "")
                        gap_lines.append(f"    • Documento mancante: {desc}")
                    for me in req["missing_evidences"]:
                        desc = me.get("description") or me.get("type", "")
                        gap_lines.append(f"    • Evidenza mancante: {desc}")
                    for ee in req["expired_evidences"]:
                        gap_lines.append(
                            f"    • Evidenza scaduta: {ee.get('title','')} "
                            f"(scaduta il {ee.get('expired_on','')})"
                        )
                if gap_lines or ctrl["status"] in ("gap",):
                    mancanze.append(
                        f"\n[{ctrl['external_id']}] {ctrl['title']} — Stato: {ctrl['status']}"
                    )
                    mancanze.extend(gap_lines)

            if mancanze:
                mancanze_txt = (
                    f"# MANCANZE / GAP — {zip_fw_label} — {today.isoformat()}\n"
                    "# I controlli N/A (fuori trattamento) sono esclusi da questo file.\n"
                    + "\n".join(mancanze)
                )
            else:
                mancanze_txt = (
                    f"# Nessuna mancanza rilevata — {zip_fw_label} — {today.isoformat()}\n"
                    "# Tutti i controlli in trattamento hanno evidenze complete e valide.\n"
                )
            zf.writestr(f"{zip_name}/MANCANZE.txt", mancanze_txt.encode("utf-8"))

            # ── Programma audit annuale ────────────────────────────────────────
            _add_audit_programs(zf, zip_name, fw_codes, plant_id, today)

            # ── Revisioni di direzione ─────────────────────────────────────────
            _add_management_reviews(zf, zip_name, plant_id, default_storage)
            _add_management_review_reports(zf, zip_name, plant_id)

            # ── Audit esterni (seconda/terza parte) con rapporti ufficiali ─────
            _add_external_audit_reports(zf, zip_name, plant_id, default_storage)

            # ── Registro rischi ────────────────────────────────────────────────
            _add_risk_register(zf, zip_name, plant_id)

            # ── Cartelle per controllo ─────────────────────────────────────────
            for ctrl in controls_list:
                safe_title = _sanitize_name(ctrl["title"], 60)
                folder = f"{ctrl['external_id']} - {safe_title}"

                # Documenti collegati
                for doc in ctrl["doc_objects"]:
                    version = doc.versions.order_by("-version_number").first()
                    if not version or not version.storage_path:
                        continue
                    if not default_storage.exists(version.storage_path):
                        continue
                    try:
                        content = default_storage.open(version.storage_path, "rb").read()
                        _, ext = _os.path.splitext(version.file_name or version.storage_path)
                        prefix = (doc.document_code + "_") if doc.document_code else ""
                        safe_doc = _sanitize_name(doc.title, 50)
                        fname = f"{prefix}{safe_doc}{ext}"
                        zf.writestr(f"{zip_name}/{folder}/documenti/{fname}", content)
                    except Exception:
                        pass

                # Evidenze collegate
                for ev in ctrl["ev_objects"]:
                    if not ev.file_path or not default_storage.exists(ev.file_path):
                        continue
                    try:
                        content = default_storage.open(ev.file_path, "rb").read()
                        _, ext = _os.path.splitext(ev.file_path)
                        safe_ev = _sanitize_name(ev.title, 50)
                        fname = f"{safe_ev}{ext}"
                        zf.writestr(f"{zip_name}/{folder}/evidenze/{fname}", content)
                    except Exception:
                        pass

        log_action(
            user=request.user,
            action_code="controls.audit_package.download",
            level="L2",
            entity=plant,
            payload={
                "framework": zip_fw_label,
                "plant_id": str(plant_id) if plant_id else None,
                "controls_count": len(controls_list),
                "zip_name": zip_name,
            },
        )

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_name}.zip"'
        return response
