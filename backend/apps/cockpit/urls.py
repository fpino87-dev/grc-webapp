from django.urls import path

from .views import (
    CockpitAssistantView,
    CockpitExplainView,
    CockpitInsightActionView,
    CockpitInsightsView,
    CockpitTrendView,
)

urlpatterns = [
    path("insights/", CockpitInsightsView.as_view(), name="cockpit-insights"),
    # explain prima della route generica <action> (altrimenti 'explain' la intercetta)
    path("insights/<str:fingerprint>/explain/", CockpitExplainView.as_view(), name="cockpit-insight-explain"),
    path("insights/<str:fingerprint>/<str:action>/", CockpitInsightActionView.as_view(), name="cockpit-insight-action"),
    path("assistant/", CockpitAssistantView.as_view(), name="cockpit-assistant"),
    path("posture-trend/", CockpitTrendView.as_view(), name="cockpit-posture-trend"),
]
