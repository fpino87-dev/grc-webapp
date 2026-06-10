from rest_framework.response import Response
from rest_framework.views import APIView

from ..permissions import ControlsReportPermission


class GapAnalysisView(APIView):
    permission_classes = [ControlsReportPermission]

    def get(self, request):
        from ..services import gap_analysis
        from django.utils.translation import gettext as _
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        plant_id = request.query_params.get("plant")
        if not source or not target:
            return Response({"error": _("Parametri 'source' e 'target' obbligatori.")}, status=400)
        lang = request.query_params.get("lang") or getattr(request, "LANGUAGE_CODE", None) or "it"
        result = gap_analysis(source, target, plant_id, lang=lang)
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
