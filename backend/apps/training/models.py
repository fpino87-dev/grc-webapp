from django.db import models
from django.contrib.auth import get_user_model

from core.models import BaseModel

User = get_user_model()


class TrainingCourse(BaseModel):
    SOURCE_CHOICES = [("interno", "Interno"), ("kb4", "KnowBe4"), ("esterno", "Esterno")]
    STATUS_CHOICES = [("attivo", "Attivo"), ("archiviato", "Archiviato")]

    title = models.CharField(max_length=300)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="interno")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="attivo")
    kb4_campaign_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    mandatory = models.BooleanField(default=False)
    framework_refs = models.JSONField(default=list)
    plants = models.ManyToManyField("plants.Plant", blank=True, related_name="training_courses")
    deadline = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class TrainingEnrollment(BaseModel):
    STATUS_CHOICES = [
        ("assegnato", "Assegnato"),
        ("in_corso", "In corso"),
        ("completato", "Completato"),
        ("scaduto", "Scaduto"),
    ]

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_enrollments")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="assegnato")
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = [["course", "user"]]
        ordering = ["-created_at"]


class PhishingSimulation(BaseModel):
    RESULT_CHOICES = [
        ("clicked", "Clicked"),
        ("reported", "Reported"),
        ("ignored", "Ignored"),
    ]

    kb4_simulation_id = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phishing_results")
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT, null=True, blank=True)
    result = models.CharField(max_length=15, choices=RESULT_CHOICES)
    sent_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
