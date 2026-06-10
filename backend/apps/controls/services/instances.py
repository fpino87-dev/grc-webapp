from ..models import ControlInstance
from .evidence import check_evidence_requirements


def evaluate_control(instance, new_status, user, note=""):
    from django.core.exceptions import ValidationError
    from django.utils import timezone
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if new_status in ("compliant", "parziale"):
        req_check = check_evidence_requirements(instance)

        if new_status == "compliant" and not req_check["satisfied"]:
            msgs = []
            for md in req_check["missing_documents"]:
                msgs.append(_("• Documento mancante: %(desc)s") % {"desc": md["description"] or md["type"]})
            for me in req_check["missing_evidences"]:
                msgs.append(_("• Evidenza mancante: %(desc)s") % {"desc": me["description"] or me["type"]})
            for ee in req_check["expired_evidences"]:
                msgs.append(
                    _("• Evidenza scaduta: %(title)s (scaduta il %(date)s)") % {
                        "title": ee["title"],
                        "date": ee["expired_on"],
                    }
                )
            # Fallback: if no evidence_requirement defined, require at least one valid evidence
            if not msgs:
                today = timezone.localdate()
                if not instance.evidences.filter(valid_until__gte=today, deleted_at__isnull=True).exists():
                    raise ValidationError(
                        _("Impossibile impostare lo stato a 'compliant' senza almeno un'evidenza valida collegata.")
                    )
            else:
                raise ValidationError(
                    _("Requisiti non soddisfatti per stato Compliant:\n") + "\n".join(msgs)
                )

        if new_status == "parziale":
            today = timezone.localdate()
            has_any = (
                instance.evidences.filter(
                    valid_until__gte=today, deleted_at__isnull=True
                ).exists()
                or instance.documents.filter(
                    status="approvato", deleted_at__isnull=True
                ).exists()
            )
            if not has_any:
                raise ValidationError(
                    _("Almeno un documento approvato o un'evidenza valida richiesti per stato Parziale.")
                )

    if new_status == "na":
        if not note or len(note.strip()) < 20:
            raise ValidationError(
                _("Lo stato N/A richiede una giustificazione scritta di almeno 20 caratteri.")
            )

    instance.status = new_status
    instance.last_evaluated_at = timezone.now()
    instance.last_evaluated_note = note
    update_fields = ["status", "last_evaluated_at", "last_evaluated_note", "updated_at"]
    if new_status == "na":
        instance.na_justification = note
        update_fields.append("na_justification")
    # Valutare il controllo È la rivalutazione: chiude il flag "da rivalutare".
    # Prima non veniva azzerato da nessuna parte → un controllo flaggato da un
    # change asset restava "da rivalutare" a vita anche dopo essere stato rivalutato.
    if instance.needs_revaluation:
        instance.needs_revaluation = False
        instance.needs_revaluation_since = None
        update_fields += ["needs_revaluation", "needs_revaluation_since"]
    instance.save(update_fields=update_fields)

    log_action(
        user=user,
        action_code="control.evaluated",
        level="L2",
        entity=instance,
        payload={
            "new_status": new_status,
            "note": note,
            "evidences_count": instance.evidences.count(),
            "documents_count": instance.documents.count(),
        },
    )
    return instance


def validate_exclusion(instance, applicability: str,
                       justification: str, user) -> None:
    """
    Valida e applica una modifica di applicabilità.
    Se escluso: richiede giustificazione di almeno 50 caratteri.
    Aggiorna status a 'na' se escluso.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from core.audit import log_action

    if applicability == "escluso":
        if not justification or len(justification.strip()) < 50:
            raise ValidationError(
                _("La giustificazione di esclusione per SOA richiede almeno 50 caratteri. Specificare il motivo formale per cui il controllo non è applicabile.")
            )

    instance.applicability = applicability
    instance.exclusion_justification = justification
    if applicability == "escluso":
        instance.status = "na"
        instance.na_justification = justification
    instance.save(update_fields=[
        "applicability", "exclusion_justification",
        "status", "na_justification", "updated_at",
    ])

    log_action(
        user=user,
        action_code="control.applicability_changed",
        level="L2",
        entity=instance,
        payload={
            "applicability": applicability,
            "justification": justification[:100],
        },
    )


def delete_control_instance(instance, user) -> None:
    """
    Soft delete di un'istanza controllo per plant.
    Consentita solo se lo stato è ancora «non_valutato», salvo superuser.
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if instance.status != "non_valutato" and not getattr(user, "is_superuser", False):
        raise ValidationError(
            _("Eliminazione consentita solo per controlli non ancora valutati.")
        )

    instance.documents.clear()
    instance.evidences.clear()
    instance.soft_delete()

    log_action(
        user=user,
        action_code="controls.instance.delete",
        level="L2",
        entity=instance,
        payload={
            "id": str(instance.id),
            "plant_id": str(instance.plant_id),
            "control_id": str(instance.control_id),
            "framework": instance.control.framework.code,
            "external_id": instance.control.external_id,
        },
    )


# ---------------------------------------------------------------------------
# Propagazione cross-framework (e opzionalmente cross-plant)
# ---------------------------------------------------------------------------

_PROPAGABLE_STATUSES = {"compliant", "na"}
# equivalente → bidirezionale; covers → solo sorgente→target
_PROPAGABLE_RELATIONSHIPS = {"equivalente", "covers"}


def propagate_control(instance, user, cross_plant: bool = False) -> dict:
    """
    Propaga lo stato dell'istanza ai controlli mappati rispettando
    tipo di relazione e direzione.

    Regole:
    - Solo stati 'compliant' e 'na' sono propagabili.
    - 'equivalente'  → bidirezionale (A≡B, quindi B≡A)
    - 'covers'       → solo source → target  (A copre B; B non copre A)
    - 'parziale', 'correlato', 'extends' → ignorati (valutazione separata)
    - cross_plant=False → solo stesso plant
    - cross_plant=True  → tutti i plant che hanno un'istanza del controllo target

    Non esegue la validazione delle evidenze: la propagazione copia il dato
    già validato sul controllo sorgente.

    Returns: {"propagated_to": int, "skipped_no_instance": int}
    """
    from core.audit import log_action
    from django.utils import timezone

    if instance.status not in _PROPAGABLE_STATUSES:
        return {"propagated_to": 0, "skipped_no_instance": 0, "blocked": "status_not_propagable"}

    target_control_ids: set = set()

    # source → target: ok per equivalente e covers
    for m in instance.control.mappings_from.filter(relationship__in=_PROPAGABLE_RELATIONSHIPS):
        target_control_ids.add(m.target_control_id)

    # target → source: solo per equivalente (simmetria)
    for m in instance.control.mappings_to.filter(relationship="equivalente"):
        target_control_ids.add(m.source_control_id)

    if not target_control_ids:
        return {"propagated_to": 0, "skipped_no_instance": 0}

    qs = ControlInstance.objects.filter(
        control_id__in=target_control_ids,
        deleted_at__isnull=True,
    )
    if not cross_plant:
        qs = qs.filter(plant=instance.plant)

    note_origin = instance.na_justification or instance.last_evaluated_note or ""
    note_for_target = f"Propagato da {instance.control.external_id}" + (
        f": {note_origin}" if note_origin else ""
    )

    propagated = 0
    skipped = 0

    for target in qs.select_related("control", "plant"):
        if target.pk == instance.pk:
            continue
        target.status = instance.status
        target.last_evaluated_at = timezone.now()
        target.last_evaluated_note = note_for_target
        update_fields = ["status", "last_evaluated_at", "last_evaluated_note", "updated_at"]
        if instance.status == "na":
            target.na_justification = note_for_target
            update_fields.append("na_justification")
        target.save(update_fields=update_fields)

        log_action(
            user=user,
            action_code="control.propagated",
            level="L2",
            entity=target,
            payload={
                "source_instance": str(instance.pk),
                "source_control": instance.control.external_id,
                "source_plant": str(instance.plant_id),
                "propagated_status": instance.status,
                "cross_plant": cross_plant,
            },
        )
        propagated += 1

    return {"propagated_to": propagated, "skipped_no_instance": skipped}
