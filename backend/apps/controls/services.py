from .models import Control, ControlInstance


def check_evidence_requirements(instance) -> dict:
    """
    Verifica se ControlInstance soddisfa i requisiti definiti
    in Control.evidence_requirement.
    """
    from django.utils import timezone

    today = timezone.now().date()
    req = instance.control.evidence_requirement or {}
    result = {
        "satisfied": True,
        "missing_documents": [],
        "missing_evidences": [],
        "expired_evidences": [],
        "warnings": [],
    }

    # Controlla documenti richiesti
    for doc_req in req.get("documents", []):
        if not doc_req.get("mandatory"):
            continue
        doc_type = doc_req.get("type")
        exists = instance.documents.filter(
            document_type=doc_type,
            status="approvato",
            deleted_at__isnull=True,
        ).exists()
        if not exists:
            result["satisfied"] = False
            result["missing_documents"].append({
                "type": doc_type,
                "description": doc_req.get("description", ""),
            })

    # Controlla evidenze richieste
    for ev_req in req.get("evidences", []):
        if not ev_req.get("mandatory"):
            continue
        ev_type = ev_req.get("type")
        max_age = ev_req.get("max_age_days")
        description = ev_req.get("description", "")

        ev_qs = instance.evidences.filter(
            evidence_type=ev_type,
            deleted_at__isnull=True,
        )
        if not ev_qs.exists():
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": ev_type,
                "description": description,
            })
            continue

        for ev in ev_qs:
            if ev.valid_until and ev.valid_until < today:
                result["expired_evidences"].append({
                    "id": str(ev.id),
                    "title": ev.title,
                    "expired_on": str(ev.valid_until),
                })
                result["satisfied"] = False
            elif max_age and ev.created_at:
                age = (today - ev.created_at.date()).days
                if age > max_age:
                    result["warnings"].append(
                        f"Evidenza '{ev.title}' ha {age} giorni "
                        f"(max consigliato: {max_age}gg)"
                    )

    # Controlla minimi
    min_docs = req.get("min_documents", 0)
    min_evs = req.get("min_evidences", 0)
    if min_docs > 0:
        count = instance.documents.filter(
            status="approvato", deleted_at__isnull=True
        ).count()
        if count < min_docs:
            result["satisfied"] = False
            result["missing_documents"].append({
                "type": "any",
                "description": f"Richiesti almeno {min_docs} documenti approvati",
            })
    if min_evs > 0:
        count = instance.evidences.filter(
            valid_until__gte=today, deleted_at__isnull=True
        ).count()
        if count < min_evs:
            result["satisfied"] = False
            result["missing_evidences"].append({
                "type": "any",
                "description": f"Richieste almeno {min_evs} evidenze valide",
            })

    return result


def evaluate_control(instance, new_status, user, note=""):
    from django.core.exceptions import ValidationError
    from django.utils import timezone

    from core.audit import log_action

    if new_status in ("compliant", "parziale"):
        req_check = check_evidence_requirements(instance)

        if new_status == "compliant" and not req_check["satisfied"]:
            msgs = []
            for md in req_check["missing_documents"]:
                msgs.append(f"• Documento mancante: {md['description'] or md['type']}")
            for me in req_check["missing_evidences"]:
                msgs.append(f"• Evidenza mancante: {me['description'] or me['type']}")
            for ee in req_check["expired_evidences"]:
                msgs.append(f"• Evidenza scaduta: {ee['title']} (scaduta il {ee['expired_on']})")
            # Fallback: if no evidence_requirement defined, require at least one valid evidence
            if not msgs:
                today = timezone.now().date()
                if not instance.evidences.filter(valid_until__gte=today, deleted_at__isnull=True).exists():
                    raise ValidationError(
                        "Impossibile impostare lo stato a 'compliant' senza almeno "
                        "un'evidenza valida collegata."
                    )
            else:
                raise ValidationError(
                    "Requisiti non soddisfatti per stato Compliant:\n" + "\n".join(msgs)
                )

        if new_status == "parziale":
            today = timezone.now().date()
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
                    "Almeno un documento approvato o un'evidenza valida "
                    "richiesti per stato Parziale."
                )

    if new_status == "na":
        if not note or len(note.strip()) < 20:
            raise ValidationError(
                "Lo stato N/A richiede una giustificazione scritta "
                "di almeno 20 caratteri."
            )

    instance.status = new_status
    instance.last_evaluated_at = timezone.now()
    instance.last_evaluated_note = note
    instance.save(update_fields=[
        "status", "last_evaluated_at", "last_evaluated_note", "updated_at"
    ])

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


def gap_analysis(source_framework_code: str, target_framework_code: str, plant_id) -> dict:
    """
    Confronta due framework e mostra cosa manca per passare dall'uno all'altro.
    """
    from .models import Control, ControlInstance, ControlMapping

    target_controls = Control.objects.filter(
        framework__code=target_framework_code,
        deleted_at__isnull=True,
    ).prefetch_related("mappings_to__source_control")

    result = {
        "source_framework": source_framework_code,
        "target_framework": target_framework_code,
        "covered":    [],
        "partial":    [],
        "gap":        [],
        "not_mapped": [],
        "summary":    {},
    }

    for tc in target_controls:
        mappings = tc.mappings_to.filter(
            source_control__framework__code=source_framework_code
        )
        if not mappings.exists():
            result["not_mapped"].append({
                "id": str(tc.pk),
                "external_id": tc.external_id,
                "title": tc.get_title("it"),
                "domain": tc.domain.get_name("it") if tc.domain else "",
            })
            continue

        best_status = "non_valutato"
        for mapping in mappings:
            try:
                ci = ControlInstance.objects.get(
                    plant_id=plant_id,
                    control=mapping.source_control,
                )
                order = {"compliant": 4, "parziale": 3, "na": 2, "gap": 1, "non_valutato": 0}
                if order.get(ci.status, 0) > order.get(best_status, 0):
                    best_status = ci.status
            except ControlInstance.DoesNotExist:
                pass

        entry = {
            "id": str(tc.pk),
            "external_id": tc.external_id,
            "title": tc.get_title("it"),
            "domain": tc.domain.get_name("it") if tc.domain else "",
            "source_status": best_status,
        }
        if best_status == "compliant":
            result["covered"].append(entry)
        elif best_status == "parziale":
            result["partial"].append(entry)
        else:
            result["gap"].append(entry)

    total = target_controls.count()
    result["summary"] = {
        "total":      total,
        "covered":    len(result["covered"]),
        "partial":    len(result["partial"]),
        "gap":        len(result["gap"]),
        "not_mapped": len(result["not_mapped"]),
        "pct_ready":  round(len(result["covered"]) / total * 100, 1) if total else 0,
    }
    return result


def get_compliance_summary(plant_id, framework_code=None):
    qs = ControlInstance.objects.filter(plant_id=plant_id)
    if framework_code:
        qs = qs.filter(control__framework__code=framework_code)
    total = qs.count()
    if total == 0:
        return {"total": 0, "compliant": 0, "gap": 0, "parziale": 0, "na": 0, "non_valutato": 0, "pct_compliant": 0}
    from django.db.models import Count

    counts = qs.values("status").annotate(n=Count("id"))
    result = {r["status"]: r["n"] for r in counts}
    compliant = result.get("compliant", 0)
    return {
        "total": total,
        "compliant": compliant,
        "gap": result.get("gap", 0),
        "parziale": result.get("parziale", 0),
        "na": result.get("na", 0),
        "non_valutato": result.get("non_valutato", 0),
        "pct_compliant": round(compliant / total * 100, 1),
    }
