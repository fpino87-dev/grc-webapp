from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AiConfirmView, AiProviderConfigViewSet, AiSuggestView

router = DefaultRouter()
router.register("config", AiProviderConfigViewSet, basename="ai-config")

urlpatterns = [
    path("", include(router.urls)),
    path("suggest/", AiSuggestView.as_view(), name="ai-suggest"),
    path("confirm/", AiConfirmView.as_view(), name="ai-confirm"),
]

