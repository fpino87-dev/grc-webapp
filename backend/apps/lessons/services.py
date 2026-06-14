from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.audit import log_action
from core.scoping import user_can_access_plant
from .models import LessonLearned


@transaction.atomic
def validate_lesson(lesson: LessonLearned, user) -> LessonLearned:
    """Transizione bozza → validato (controllo SoD: chi valida traccia se stesso)."""
    if lesson.status != "bozza":
        raise ValidationError(
            _("Solo una lezione in bozza può essere validata (stato attuale: %(s)s).")
            % {"s": lesson.status}
        )
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


@transaction.atomic
def propagate_to_plants(lesson: LessonLearned, plant_ids: list, user) -> LessonLearned:
    """Propaga una lezione validata ad altri siti.

    Vincoli:
      * la lezione deve essere già `validato`/`propagato` (workflow);
      * l'utente deve avere accesso a ciascun sito di destinazione — la
        condivisione cross-plant è ristretta al perimetro dell'utente, lo
        scoping dei queryset non copre i plant passati nel body (sweep security
        per-sito).
    """
    if lesson.status not in ("validato", "propagato"):
        raise ValidationError(
            _("La lezione deve essere validata prima di poter essere propagata.")
        )

    from apps.plants.models import Plant

    valid_ids = list(
        Plant.objects.filter(pk__in=plant_ids, deleted_at__isnull=True).values_list("pk", flat=True)
    )
    for pid in valid_ids:
        if not user_can_access_plant(user, pid):
            raise PermissionDenied(_("Accesso negato per uno dei siti di destinazione."))

    lesson.propagated_to_plants.set(valid_ids)
    lesson.status = "propagato"
    lesson.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action_code="lessons.lesson_learned.propagate",
        level="L2",
        entity=lesson,
        payload={"id": str(lesson.id), "plant_ids": [str(p) for p in valid_ids]},
    )
    return lesson
