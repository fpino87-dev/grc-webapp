"""Centro Operativo (M21) — API.

GET insights (aggregati + posture), azioni snooze/accept/reopen (anti alert-fatigue)
e trend storico della postura.
"""
import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import CockpitPermission


def _resolve_plant(request):
    """Risolve `?plant=` verificando l'accesso dell'utente al sito; senza plant
    la vista è aggregata sulla postura di TUTTI i siti → solo scope org
    (sweep security 2026-06-12, pattern gap-analysis)."""
    from core.scoping import require_plant_access

    plant_id = request.query_params.get("plant")
    require_plant_access(request.user, plant_id or None)
    if not plant_id:
        return None, None
    from apps.plants.models import Plant
    return plant_id, Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()


class CockpitInsightsView(APIView):
    """GET /api/v1/cockpit/insights/?plant=&mine=1&include_suppressed=1"""

    permission_classes = [CockpitPermission]

    def get(self, request):
        from apps.cockpit.services import build_cockpit

        _, plant = _resolve_plant(request)
        mine = request.query_params.get("mine") in ("1", "true", "yes")
        include_suppressed = request.query_params.get("include_suppressed") in ("1", "true", "yes")
        return Response(build_cockpit(
            plant=plant, user=request.user, mine=mine, include_suppressed=include_suppressed,
        ))


class CockpitInsightActionView(APIView):
    """POST /api/v1/cockpit/insights/<fingerprint>/<action>/  (snooze|accept|reopen)

    Body: `{ "until": "YYYY-MM-DD" (snooze/accept), "note": "..." (opzionale) }`.
    """

    permission_classes = [CockpitPermission]
    _ACTIONS = {"snooze", "accept", "reopen"}

    def post(self, request, fingerprint, action):
        from apps.cockpit.services import apply_insight_action

        if action not in self._ACTIONS:
            return Response({"detail": "azione non valida."}, status=status.HTTP_400_BAD_REQUEST)

        until = None
        if action in ("snooze", "accept"):
            raw = (request.data.get("until") or "").strip()
            if raw:
                try:
                    until = datetime.date.fromisoformat(raw)
                except ValueError:
                    return Response({"detail": "data 'until' non valida (YYYY-MM-DD)."},
                                    status=status.HTTP_400_BAD_REQUEST)
        note = (request.data.get("note") or "").strip()

        st = apply_insight_action(fingerprint, action, until=until, note=note, user=request.user)
        if st is None:
            return Response({"detail": "insight non trovato."}, status=status.HTTP_404_NOT_FOUND)

        from core.audit import log_action
        log_action(
            user=request.user, action_code=f"cockpit.insight_{action}", level="L1",
            entity=st, payload={"fingerprint": fingerprint, "code": st.code,
                                "until": until.isoformat() if until else None},
        )
        return Response({"fingerprint": fingerprint, "status": st.status,
                         "snoozed_until": st.snoozed_until.isoformat() if st.snoozed_until else None,
                         "accepted_until": st.accepted_until.isoformat() if st.accepted_until else None,
                         "note": st.note})


class CockpitExplainView(APIView):
    """POST /api/v1/cockpit/insights/<fingerprint>/explain/ — spiegazione + bozza
    di remediation (M20). Output solo proposto, mai applicato (human-in-the-loop)."""

    permission_classes = [CockpitPermission]

    def get_throttles(self):
        from core.jwt import AiRateThrottle
        return [AiRateThrottle()]

    def post(self, request, fingerprint):
        from apps.cockpit.services import ai_explain_insight
        from apps.ai_engine.router import LlmUnavailable

        try:
            out = ai_explain_insight(fingerprint, user=request.user)
        except LlmUnavailable:
            return Response({"detail": "Servizio AI non disponibile. Riprova più tardi."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if out is None:
            return Response({"detail": "insight non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(out)


class CockpitAssistantView(APIView):
    """POST /api/v1/cockpit/assistant/ — assistente RAG grounded sugli insight.
    Body: `{ "question": "...", "plant": "<uuid>" (opzionale) }`."""

    permission_classes = [CockpitPermission]

    def get_throttles(self):
        from core.jwt import AiRateThrottle
        return [AiRateThrottle()]

    def post(self, request):
        from apps.cockpit.services import ai_assistant
        from apps.ai_engine.router import LlmUnavailable

        question = (request.data.get("question") or "").strip()
        if not question:
            return Response({"detail": "domanda mancante."}, status=status.HTTP_400_BAD_REQUEST)

        plant = None
        plant_id = request.data.get("plant") or request.query_params.get("plant")
        from core.scoping import require_plant_access
        require_plant_access(request.user, plant_id or None)
        if plant_id:
            from apps.plants.models import Plant
            plant = Plant.objects.filter(pk=plant_id, deleted_at__isnull=True).first()

        try:
            out = ai_assistant(question, plant=plant, user=request.user)
        except LlmUnavailable:
            return Response({"detail": "Servizio AI non disponibile. Riprova più tardi."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(out)


class CockpitTrendView(APIView):
    """GET /api/v1/cockpit/posture-trend/?plant=&days=90 — storico Posture Score."""

    permission_classes = [CockpitPermission]

    def get(self, request):
        from apps.cockpit.models import PostureSnapshot

        plant_id, _ = _resolve_plant(request)
        try:
            days = min(int(request.query_params.get("days", 90)), 366)
        except (TypeError, ValueError):
            days = 90
        import datetime as _dt
        from django.utils import timezone
        since = timezone.localdate() - _dt.timedelta(days=days)

        qs = (PostureSnapshot.objects
              .filter(plant_id=plant_id if plant_id else None, taken_on__gte=since, deleted_at__isnull=True)
              .order_by("taken_on")
              .values("taken_on", "total", "counts"))
        return Response({"points": [
            {"date": r["taken_on"].isoformat(), "total": r["total"], "counts": r["counts"]} for r in qs
        ]})
