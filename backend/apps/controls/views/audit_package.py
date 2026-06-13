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

    qs = ManagementReview.objects.filter(
        deleted_at__isnull=True,
        status="completato",
    ).select_related("chair", "approved_by")
    if plant_id:
        qs = qs.filter(plant_id=plant_id)

    reviews = list(qs.order_by("-review_date"))
    if not reviews:
        return

    # Riepilogo CSV
    buf = io.StringIO()
    w = safe_writer(buf)
    w.writerow(["Data", "Titolo", "Presidente", "Stato approvazione",
                "Approvato da", "Approvato il", "Prossima revisione",
                "N. delibere", "Verbale allegato"])
    for r in reviews:
        has_doc = bool(r.document_id)
        w.writerow([
            r.review_date.isoformat(),
            r.title,
            r.chair.get_full_name() if r.chair else "—",
            r.approval_status,
            r.approved_by.get_full_name() if r.approved_by else "—",
            r.approved_at.strftime("%Y-%m-%d") if r.approved_at else "—",
            r.next_review_date.isoformat() if r.next_review_date else "—",
            len(r.delibere) if isinstance(r.delibere, list) else 0,
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
