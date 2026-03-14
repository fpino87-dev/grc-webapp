from django.utils import timezone
from core.audit import log_action
from .models import LessonLearned


def validate_lesson(lesson: LessonLearned, user) -> LessonLearned:
    """Transition a lesson from bozza to validato."""
    lesson.status = "validato"
    lesson.validated_by = user
    lesson.validated_at = timezone.now()
    lesson.save(update_fields=["status", "validated_by", "validated_at", "updated_at"])
    log_action(
        user=user,
        action_code="lessons.lesson_learned.validate",
        level="L2",
        entity=lesson,
        payload={"id": str(lesson.id), "title": lesson.title},
    )
    return lesson


def propagate_to_plants(lesson: LessonLearned, plant_ids: list, user) -> LessonLearned:
    """Propagate a validated lesson to additional plants."""
    lesson.propagated_to_plants.set(plant_ids)
    lesson.status = "propagato"
    lesson.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action_code="lessons.lesson_learned.propagate",
        level="L2",
        entity=lesson,
        payload={"id": str(lesson.id), "plant_ids": [str(p) for p in plant_ids]},
    )
    return lesson
