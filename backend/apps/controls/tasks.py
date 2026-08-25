import logging

from celery import shared_task
from django.utils import timezone


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_expired_evidences():
    """
    Eseguito ogni notte alle 02:00.
    Per ogni ControlInstance compliant con requisiti non soddisfatti
    (evidenze scadute o mancanti, documenti mancanti):
    - degrada a "parziale"
    - crea task al control owner con titolo appropriato:
        * "Evidenza scaduta" se ci sono evidenze con valid_until < oggi
        * "Nessuna evidenza valida" se i requisiti non sono soddisfatti ma senza scadute
    I controlli che richiedono solo documenti (policy/procedure) non vengono
    degradati se i documenti obbligatori sono presenti.
    """
    from .models import ControlInstance
    from .services import check_evidence_requirements
    from apps.tasks.services import create_task
    from core.audit import log_action
    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = timezone.localdate()
    system_user = User.objects.filter(is_superuser=True).first()

    from django.db.models import Exists, OuterRef
    from apps.plants.models import PlantFramework

    # Salta istanze il cui plant non ha più il framework associato (es. dopo rimozione PlantFramework)
    active_pf = PlantFramework.objects.filter(
        plant=OuterRef("plant"),
        framework=OuterRef("control__framework"),
    )

    instances = ControlInstance.objects.filter(
        status="compliant",
        deleted_at__isnull=True,
    ).annotate(
        has_active_pf=Exists(active_pf),
    ).filter(
        has_active_pf=True,
    ).select_related("control", "plant", "owner").prefetch_related("evidences", "documents")

    degraded = 0
    for instance in instances:
        req_check = check_evidence_requirements(instance)

        if req_check["satisfied"]:
            continue

        # Distingui: evidenze scadute vs requisiti mai soddisfatti
        has_expired = bool(req_check["expired_evidences"])
        if has_expired:
            task_title = f"Evidenza scaduta — {instance.control.external_id}"
            task_description = (
                f"Il controllo {instance.control.external_id} era Compliant "
                f"ma le evidenze collegate sono scadute. "
                f"Carica una nuova evidenza per ripristinare lo stato."
            )
        else:
            task_title = f"Nessuna evidenza valida — {instance.control.external_id}"
            task_description = (
                f"Il controllo {instance.control.external_id} era Compliant "
                f"ma non ha evidenze o documenti validi collegati. "
                f"Collega un'evidenza o un documento approvato per ripristinare lo stato."
            )

        instance.status = "parziale"
        instance.save(update_fields=["status", "updated_at"])
        degraded += 1

        if instance.owner:
            create_task(
                plant=instance.plant,
                title=task_title,
                description=task_description,
                priority="alta",
                source_module="M03",
                source_id=instance.pk,
                due_date=today + timezone.timedelta(days=15),
                assign_type="user",
                assign_value=str(instance.owner.pk),
                control_instance=instance,
            )

        if system_user:
            log_action(
                user=system_user,
                action_code="control.evidence_expired",
                level="L2",
                entity=instance,
                payload={
                    "degraded_to": "parziale",
                    "date": str(today),
                    "has_expired_evidences": has_expired,
                },
            )

        try:
            from apps.notifications.resolver import fire_notification

            fire_notification(
                "evidence_expired",
                plant=instance.plant,
                context={"instance": instance},
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("controls: notifica evidenza scaduta non inviata: %s", exc)

    return f"check_expired_evidences: {degraded} controlli degradati"


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def check_control_reviews_due():
    """
    Eseguito ogni notte. Gestisce la riverifica periodica dei controlli
    (semestrale, annuale, … secondo la policy del sito o la cadenza indicata
    sul singolo controllo):

    - completa `next_review_date` sui controlli già valutati che ne sono
      ancora privi, calcolandola dall'ultima valutazione o, se manca, da oggi
      (recupero dello storico: senza, un controllo valutato prima di questa
      funzione non sarebbe mai stato riverificato);
    - quando la scadenza rientra nella soglia di preavviso della policy,
      marca il controllo `needs_revaluation` e crea un task all'owner.

    Il flag viene azzerato dalla valutazione (`evaluate_control`), che
    ricalcola anche la scadenza successiva: nessun task duplicato finché il
    controllo resta da rivalutare.
    """
    from apps.plants.services import plant_today
    from core.periodic import due_status
    from apps.tasks.services import create_task
    from core.audit import log_action
    from django.contrib.auth import get_user_model

    from .models import ControlInstance
    from .services import EVALUATED_STATUSES, apply_review_schedule

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()

    base_qs = ControlInstance.objects.filter(
        deleted_at__isnull=True,
        applicability="applicabile",
        status__in=EVALUATED_STATUSES,
    ).select_related("control", "plant", "owner")

    # 1) Recupero: controlli valutati senza data di riverifica. Si conta
    #    dall'ultima valutazione; per i controlli importati con uno stato ma
    #    senza data di valutazione (nessuno strumento per sapere quando sono
    #    stati guardati) il ciclo parte da oggi — meglio che lasciarli fuori
    #    dalla riverifica per sempre.
    backfilled = 0
    for instance in base_qs.filter(next_review_date__isnull=True):
        base = (
            timezone.localtime(instance.last_evaluated_at).date()
            if instance.last_evaluated_at
            else None
        )
        if apply_review_schedule(instance, base=base) is not None:
            backfilled += 1

    # 2) Riverifiche in scadenza o scadute.
    flagged = 0
    for instance in base_qs.filter(
        next_review_date__isnull=False, needs_revaluation=False
    ):
        today = plant_today(instance.plant)
        to_flag, days_left, already_due = due_status(
            instance.plant, "control_review", instance.next_review_date, today
        )
        if not to_flag:
            continue

        instance.needs_revaluation = True
        instance.needs_revaluation_since = today
        instance.save(
            update_fields=["needs_revaluation", "needs_revaluation_since", "updated_at"]
        )
        flagged += 1

        if system_user:
            log_action(
                user=system_user,
                action_code="control.review_due",
                level="L2",
                entity=instance,
                payload={
                    "control": instance.control.external_id,
                    "next_review_date": str(instance.next_review_date),
                    "days_left": days_left,
                    "already_due": already_due,
                },
            )

        if instance.owner:
            if already_due:
                title = f"Riverifica controllo SCADUTA — {instance.control.external_id}"
                description = (
                    f"La riverifica periodica del controllo {instance.control.external_id} "
                    f"era attesa entro il {instance.next_review_date}. "
                    "Rivaluta il controllo e aggiorna le evidenze collegate."
                )
                priority = "alta"
                due_days = 7
            else:
                title = (
                    f"Riverifica controllo in scadenza ({days_left}gg) — "
                    f"{instance.control.external_id}"
                )
                description = (
                    f"Il controllo {instance.control.external_id} va riverificato "
                    f"entro il {instance.next_review_date} ({days_left} giorni). "
                    "Rivaluta lo stato e verifica che le evidenze siano ancora valide."
                )
                priority = "media" if days_left > 14 else "alta"
                due_days = max(1, days_left)

            create_task(
                plant=instance.plant,
                title=title,
                description=description,
                priority=priority,
                source_module="M03",
                source_id=instance.pk,
                due_date=today + timezone.timedelta(days=due_days),
                assign_type="user",
                assign_value=str(instance.owner.pk),
                control_instance=instance,
            )

    return (
        f"check_control_reviews_due: {flagged} controlli da riverificare, "
        f"{backfilled} scadenze ricostruite"
    )
