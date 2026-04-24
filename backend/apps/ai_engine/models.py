import uuid

from django.db import models
from apps.notifications.models import EncryptedCharField

from core.models import BaseModel


class AiInteractionLog(models.Model):
    """Log append-only — human-in-the-loop obbligatorio per ogni output AI."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.UUIDField()
    function = models.CharField(max_length=50)
    module_source = models.CharField(max_length=5)
    entity_id = models.UUIDField()
    model_used = models.CharField(max_length=100)
    input_hash = models.CharField(max_length=64)  # SHA256 — MAI il testo
    output_ai = models.TextField()
    output_human_final = models.TextField(null=True, blank=True)
    delta = models.JSONField(null=True, blank=True)
    confirmed_by_id = models.UUIDField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ignored = models.BooleanField(default=False)

    class Meta:
        db_table = "ai_interaction_log"
        ordering = ["-created_at"]


PROVIDER_CHOICES = [
    ("anthropic", "Anthropic (Claude)"),
    ("openai", "OpenAI (GPT)"),
    ("groq", "Groq (Llama/Mixtral)"),
    ("google", "Google (Gemini)"),
    ("mistral", "Mistral AI"),
    ("ollama", "Ollama (locale)"),
]

MODELS_BY_PROVIDER = {
    "anthropic": [
        ("claude-haiku-4-5-20251001", "Claude Haiku (veloce, economico)"),
        ("claude-sonnet-4-6", "Claude Sonnet (bilanciato)"),
        ("claude-opus-4-6", "Claude Opus (massima qualita)"),
    ],
    "openai": [
        ("gpt-4o-mini", "GPT-4o Mini (economico)"),
        ("gpt-4o", "GPT-4o (qualita top)"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
    ],
    "groq": [
        ("llama-3.1-8b-instant", "Llama 3.1 8B (ultra veloce)"),
        ("llama-3.3-70b-versatile", "Llama 3.3 70B (qualita alta)"),
        ("mixtral-8x7b-32768", "Mixtral 8x7B"),
    ],
    "google": [
        ("gemini-1.5-flash", "Gemini 1.5 Flash (economico)"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro"),
    ],
    "mistral": [
        ("mistral-small-latest", "Mistral Small"),
        ("mistral-medium-latest", "Mistral Medium"),
    ],
    "ollama": [
        ("llama3.2:3b", "Llama 3.2 3B (consigliato CPU)"),
        ("llama3.1:8b", "Llama 3.1 8B"),
        ("mistral:7b", "Mistral 7B"),
        ("custom", "Modello personalizzato"),
    ],
}

TASK_TYPES = [
    ("incident_classify", "Classificazione incidente NIS2"),
    ("control_suggest", "Suggerimento stato controllo"),
    ("gap_actions", "Azioni correttive gap"),
    ("rca_draft", "Bozza RCA"),
    ("review_summary", "Sintesi Management Review"),
    ("chatbot", "Chatbot Ask GRC"),
    ("control_explain", "Spiegazione plain-language controllo"),
    ("osint_attack_surface", "OSINT: Analisi superficie di attacco"),
    ("osint_suppliers_nis2", "OSINT: Briefing fornitori NIS2"),
    ("osint_board_report", "OSINT: Report per Board/Audit"),
]

FALLBACK_MODES = [
    ("auto", "Automatico — passa a Ollama se cloud non disponibile"),
    ("notify", "Notifica — chiedi conferma prima del fallback"),
    ("disabled", "Disabilitato — mostra errore se cloud non disponibile"),
]


class AiProviderConfig(BaseModel):
    """
    Configurazione provider AI gestita da UI.
    """

    name = models.CharField(max_length=100, default="Configurazione AI principale")
    active = models.BooleanField(default=True)

    cloud_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="anthropic")
    cloud_model = models.CharField(max_length=100, default="claude-haiku-4-5-20251001")
    api_key = EncryptedCharField(max_length=512, blank=True, help_text="API Key cifrata AES-256")
    azure_endpoint = models.URLField(blank=True)
    azure_deployment = models.CharField(max_length=100, blank=True)

    local_endpoint = models.URLField(default="http://172.17.0.1:11434")
    local_model = models.CharField(max_length=100, default="llama3.2:3b")

    monthly_token_budget = models.IntegerField(default=100000, help_text="Token cloud massimi al mese")
    tokens_used_month = models.IntegerField(default=0)
    budget_reset_day = models.IntegerField(default=1, help_text="Giorno del mese per reset budget")
    last_budget_reset = models.DateField(null=True, blank=True)

    fallback_mode = models.CharField(max_length=10, choices=FALLBACK_MODES, default="auto")
    fallback_notified = models.BooleanField(default=False)
    task_routing = models.JSONField(default=dict, help_text="Routing per tipo task: ollama | cloud")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.active:
            AiProviderConfig.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(active=True, deleted_at__isnull=True).first()

    @property
    def budget_remaining(self) -> int:
        return max(0, self.monthly_token_budget - self.tokens_used_month)

    @property
    def budget_pct(self) -> float:
        if self.monthly_token_budget == 0:
            return 100.0
        return round(self.tokens_used_month / self.monthly_token_budget * 100, 1)

    def get_task_provider(self, task_type: str) -> str:
        defaults = {
            "incident_classify": "ollama",
            "control_suggest": "ollama",
            "gap_actions": "cloud",
            "rca_draft": "cloud",
            "review_summary": "cloud",
            "chatbot": "cloud",
            "control_explain": "cloud",
            "cpv_suggestion": "cloud",
            "generate_procedure": "cloud",
            "osint_attack_surface": "cloud",
            "osint_suppliers_nis2": "cloud",
            "osint_board_report": "cloud",
        }
        routing = self.task_routing or {}
        return routing.get(task_type, defaults.get(task_type, "ollama"))

    def reset_budget_if_needed(self):
        from django.utils import timezone

        today = timezone.now().date()
        if self.last_budget_reset is None or (
            today.day == self.budget_reset_day and today != self.last_budget_reset
        ):
            self.tokens_used_month = 0
            self.fallback_notified = False
            self.last_budget_reset = today
            self.save(
                update_fields=[
                    "tokens_used_month",
                    "fallback_notified",
                    "last_budget_reset",
                    "updated_at",
                ]
            )

