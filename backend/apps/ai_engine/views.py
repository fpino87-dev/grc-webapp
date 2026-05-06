from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_grc.permissions import IsGrcSuperAdmin
from core.audit import log_action
from core.scoping import scope_queryset_by_plant

from .models import MODELS_BY_PROVIDER, AiProviderConfig
from .permissions import AiEnginePermission
from .serializers import AiProviderConfigReadSerializer, AiProviderConfigSerializer


class AiProviderConfigViewSet(viewsets.ModelViewSet):
    queryset = AiProviderConfig.objects.all()
    serializer_class = AiProviderConfigSerializer
    permission_classes = [IsGrcSuperAdmin]
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AiProviderConfigReadSerializer
        return AiProviderConfigSerializer

    @action(detail=False, methods=["get"], url_path="models-catalog")
    def models_catalog(self, request):
        return Response(MODELS_BY_PROVIDER)

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        from .router import _call_cloud, _call_ollama

        config = self.get_object()
        results = {}
        try:
            text, tokens = _call_cloud(config, "Rispondi solo: ok", "")
            results["cloud"] = {"ok": True, "response": (text or "").strip()[:50], "tokens": tokens}
        except Exception as exc:
            results["cloud"] = {"ok": False, "error": str(exc)[:200]}
        try:
            text = _call_ollama("Rispondi solo: ok", config.local_model, config.local_endpoint)
            results["local"] = {"ok": True, "response": (text or "").strip()[:50]}
        except Exception as exc:
            results["local"] = {"ok": False, "error": str(exc)[:200]}

        log_action(user=request.user, action_code="ai.config.test", level="L3", entity=config, payload=results)
        return Response(results)

    @action(detail=True, methods=["post"], url_path="reset-budget")
    def reset_budget(self, request, pk=None):
        config = self.get_object()
        config.tokens_used_month = 0
        config.fallback_notified = False
        config.save(update_fields=["tokens_used_month", "fallback_notified", "updated_at"])
        log_action(
            user=request.user,
            action_code="ai.budget.reset",
            level="L2",
            entity=config,
            payload={"manual_reset": True},
        )
        return Response({"ok": True, "tokens_used_month": 0})


class AiSuggestView(APIView):
    permission_classes = [AiEnginePermission]

    def post(self, request):
        from .tasks_ai import classify_incident, draft_rca, suggest_gap_actions

        task_type = request.data.get("task_type")
        entity_id = request.data.get("entity_id")
        if not task_type or not entity_id:
            return Response({"error": "task_type e entity_id obbligatori"}, status=400)

        from apps.controls.models import ControlInstance
        from apps.incidents.models import Incident

        try:
            # RBAC plant scoping (S1/F7): impedisce a un utente di chiedere
            # all'AI di analizzare entità di plant cui non ha accesso.
            if task_type == "incident_classify":
                qs = scope_queryset_by_plant(Incident.objects.all(), request.user)
                entity = qs.get(pk=entity_id)
                result = classify_incident(entity, request.user)
            elif task_type == "gap_actions":
                qs = scope_queryset_by_plant(ControlInstance.objects.all(), request.user)
                entity = qs.get(pk=entity_id)
                result = suggest_gap_actions(entity, request.user)
            elif task_type == "rca_draft":
                qs = scope_queryset_by_plant(Incident.objects.all(), request.user)
                entity = qs.get(pk=entity_id)
                result = draft_rca(entity, request.user)
            else:
                return Response({"error": f"task_type '{task_type}' non supportato"}, status=400)
        except (Incident.DoesNotExist, ControlInstance.DoesNotExist):
            return Response({"error": "Entità non trovata o non accessibile."}, status=404)
        except Exception as exc:
            return Response({"error": f"Errore AI: {str(exc)[:200]}"}, status=500)

        return Response(
            {
                "task_type": task_type,
                "provider": result["provider"],
                "model": result["model"],
                "used_fallback": result["used_fallback"],
                "interaction_id": result["interaction_id"],
                "result": result.get("classification") or result.get("suggestions") or result.get("rca_draft"),
            }
        )


class AiConfirmView(APIView):
    permission_classes = [AiEnginePermission]

    def post(self, request):
        from .router import confirm_output, ignore_output

        interaction_id = request.data.get("interaction_id")
        action_type = request.data.get("action")
        final_text = request.data.get("final_text", "")

        if not interaction_id:
            return Response({"error": "interaction_id obbligatorio"}, status=400)
        if action_type == "confirm":
            confirm_output(interaction_id, request.user, final_text)
        elif action_type == "ignore":
            ignore_output(interaction_id)
        else:
            return Response({"error": "action deve essere confirm o ignore"}, status=400)
        return Response({"ok": True})


class AiAssistantStartView(APIView):
    """
    POST /api/v1/ai/assistant/start/
    Body: { "plant_id": "<uuid>" }
    Risponde con summary + lista prioritizzata di gap per il plant scelto.
    Logga l'apertura sessione in audit_log (level L2).
    """
    permission_classes = [AiEnginePermission]

    def post(self, request):
        from apps.plants.models import Plant

        from .agent_orchestrator import build_gaps, build_summary
        from .agent_tools import _verify_plant_access

        plant_id = request.data.get("plant_id")
        if not plant_id:
            return Response({"error": "plant_id obbligatorio"}, status=400)

        if not _verify_plant_access(request.user, plant_id):
            return Response({"error": "Plant non accessibile"}, status=403)

        plant = Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()
        if not plant:
            return Response({"error": "Plant non trovato"}, status=404)

        gaps, total = build_gaps(request.user, plant_id)
        summary = build_summary(request.user, plant_id)

        log_action(
            user=request.user,
            action_code="ai.assistant.start",
            level="L2",
            entity=plant,
            payload={
                "plant_id": str(plant_id),
                "gaps_returned": len(gaps),
                "gaps_total": total,
            },
        )

        return Response({
            "plant": {"id": str(plant.id), "code": plant.code, "name": plant.name},
            "summary": summary,
            "gaps": gaps,
            "gaps_total": total,
            "gaps_truncated": total > len(gaps),
        })


class AiAssistantExplainView(APIView):
    """
    POST /api/v1/ai/assistant/explain/
    Body: { "plant_id": "<uuid>", "gap": { ... gap object ... } }
    Chiama l'LLM (via route()) per spiegare un singolo gap.
    Crea AiInteractionLog HIL — l'utente puo' poi confermare/ignorare.
    """
    permission_classes = [AiEnginePermission]

    def post(self, request):
        from apps.plants.models import Plant

        from .agent_orchestrator import build_explanation_prompt
        from .agent_tools import _verify_plant_access
        from .router import route

        plant_id = request.data.get("plant_id")
        gap = request.data.get("gap")
        if not plant_id or not gap:
            return Response({"error": "plant_id e gap obbligatori"}, status=400)
        if not _verify_plant_access(request.user, plant_id):
            return Response({"error": "Plant non accessibile"}, status=403)

        plant = Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()
        if not plant:
            return Response({"error": "Plant non trovato"}, status=404)

        prompt, system = build_explanation_prompt(gap)
        try:
            result = route(
                task_type="assistant_explain",
                prompt=prompt,
                system=system,
                user=request.user,
                entity_id=plant.pk,
                module_source="M20",
                sanitize=True,
                plant_ids=[plant.pk],
                max_tokens=600,
            )
        except Exception as exc:
            return Response({"error": f"Errore LLM: {str(exc)[:200]}"}, status=500)

        log_action(
            user=request.user,
            action_code="ai.assistant.explain",
            level="L2",
            entity=plant,
            payload={
                "plant_id": str(plant_id),
                "gap_kind": gap.get("kind"),
                "gap_ref_id": gap.get("ref_id"),
                "interaction_id": result.get("interaction_id"),
                "provider": result.get("provider"),
                "used_fallback": result.get("used_fallback"),
            },
        )

        return Response({
            "explanation": result["text"],
            "interaction_id": result.get("interaction_id"),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "used_fallback": result.get("used_fallback"),
        })
