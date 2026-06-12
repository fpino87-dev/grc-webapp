from rest_framework.response import Response
from rest_framework.views import APIView

from ..permissions import ControlsReportPermission


class GapAnalysisView(APIView):
    permission_classes = [ControlsReportPermission]

    def get(self, request):
        """Gap analysis cross-framework via hub ISO (C12).

        Query: target=ISO27001|NIS2|ACN_NIS2|TISAX & plant=<uuid>
               [&profile=importante|essenziale (ACN, default dal sito)
                | AL2|AL3 (TISAX)] [&proto=true] [&lang=]
        """
        from django.utils.translation import gettext as _
        from apps.plants.models import Plant
        from ..services.gap import VALID_TARGETS, run_gap_analysis

        target = request.query_params.get("target")
        plant_id = request.query_params.get("plant")
        if not target or target not in VALID_TARGETS:
            return Response(
                {"error": _("Parametro 'target' obbligatorio (uno tra: %(targets)s).")
                 % {"targets": ", ".join(sorted(VALID_TARGETS))}},
                status=400,
            )
        plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        if not plant:
            return Response({"error": _("Parametro 'plant' obbligatorio.")}, status=400)
        # La postura di compliance di un sito è visibile solo a chi vi ha
        # accesso (security review 2026-06-12).
        from core.scoping import user_can_access_plant
        if not user_can_access_plant(request.user, plant):
            return Response({"error": _("Accesso negato per questo sito.")}, status=403)

        lang = request.query_params.get("lang") or getattr(request, "LANGUAGE_CODE", None) or "it"
        result = run_gap_analysis(
            target=target,
            plant=plant,
            profile=request.query_params.get("profile", ""),
            include_proto=request.query_params.get("proto") in ("true", "1"),
            lang=lang,
        )
        return Response(result)


class ComplianceExportView(APIView):
    permission_classes = [ControlsReportPermission]

    def get_format_suffix(self, **kwargs):
        # DRF usa 'format' come URL_FORMAT_OVERRIDE e lo intercetta dai query params.
        # Il nostro parametro ?format=soa causerebbe Http404 perché non esiste
        # nessun renderer 'soa'. Restituiamo None per disabilitare questa logica.
        return None

    FORMAT_FILENAMES = {
        "soa":               "SOA",
        "vda_isa":           "VDA_ISA",
        "compliance_matrix": "NIS2_Matrix",
    }
    FORMAT_FRAMEWORK = {
        "soa":               ["ISO27001"],
        "vda_isa":           ["TISAX_L2", "TISAX_L3", "TISAX_PROTO"],
        "compliance_matrix": ["NIS2", "ACN_NIS2"],
    }

    def get(self, request):
        from ..export_engine import generate_export
        from django.http import HttpResponse
        from django.utils import timezone
        from django.utils.translation import gettext as _

        framework_code = request.query_params.get("framework")
        plant_id = request.query_params.get("plant")
        # Usiamo "fmt" invece di "format" per evitare il conflitto con
        # DRF URL_FORMAT_OVERRIDE che intercetta "format" nei query params
        # e tenta di trovare un renderer corrispondente, causando Http404.
        export_format = request.query_params.get("fmt", "soa")

        if not framework_code:
            return Response({"error": _("Parametro 'framework' obbligatorio.")}, status=400)

        # Export = postura di compliance del sito: richiede accesso al plant;
        # senza plant l'export è aggregato su TUTTI i siti → solo scope org
        # (security review 2026-06-12).
        from core.scoping import get_user_plant_ids, user_can_access_plant
        if plant_id:
            if not user_can_access_plant(request.user, plant_id):
                return Response({"error": _("Accesso negato per questo sito.")}, status=403)
        elif get_user_plant_ids(request.user) is not None:
            return Response({"error": _("Accesso negato: export aggregato riservato allo scope organizzazione.")}, status=403)

        allowed = self.FORMAT_FRAMEWORK.get(export_format, [])
        if allowed and framework_code not in allowed:
            return Response({
                "error": _(
                    "Formato %(fmt)s non compatibile con framework %(fw)s. Usa uno di: %(allowed)s"
                ) % {
                    "fmt": export_format,
                    "fw": framework_code,
                    "allowed": ", ".join(allowed),
                }
            }, status=400)

        # Verifica che il framework sia attivo per questo plant
        if plant_id and framework_code:
            from apps.plants.services import get_active_framework_codes
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id).first()
            if plant:
                active_codes = get_active_framework_codes(plant)
                if framework_code not in active_codes:
                    return Response({
                        "error": (
                            _("Framework '%(fw)s' non attivo per questo sito. Framework attivi: %(active)s")
                            % {"fw": framework_code, "active": ", ".join(active_codes)}
                        )
                    }, status=400)

        try:
            html = generate_export(framework_code, plant_id, export_format, request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Export error [{export_format}/{framework_code}]: {traceback.format_exc()}")
            return Response(
                {"error": _("Errore generazione documento: %(err)s") % {"err": str(e)}},
                status=500,
            )

        from core.audit import log_action
        from apps.plants.models import Plant
        plant = Plant.objects.filter(pk=plant_id).first()
        if plant:
            log_action(
                user=request.user,
                action_code=f"export.{export_format}",
                level="L1",
                entity=plant,
                payload={"framework": framework_code, "format": export_format},
            )

        label = self.FORMAT_FILENAMES.get(export_format, export_format)
        filename = f"{label}_{framework_code}_{timezone.now().strftime('%Y%m%d')}.html"
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
