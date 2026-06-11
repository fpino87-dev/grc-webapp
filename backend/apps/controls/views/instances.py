from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.scoping import PlantScopedQuerysetMixin

from ..models import ControlInstance
from ..permissions import ControlInstancePermission
from ..serializers import ControlInstanceSerializer


def _explain_suggestion(instance, suggested: str, check: dict) -> str:
    """`suggested` e `check` arrivano già calcolati dal chiamante (detail_info):
    prima questa funzione li ricalcolava da zero — 2 passate in più (C2)."""
    from django.utils.translation import gettext as _

    req = instance.control.evidence_requirement or {}
    has_req = bool(
        req.get("documents") or req.get("evidences")
        or req.get("min_documents") or req.get("min_evidences")
    )
    if not has_req:
        return _("Nessun requisito documentale definito per questo controllo.")

    if suggested == "compliant":
        return _("Tutti i requisiti documentali sono soddisfatti.")

    msgs = []
    for md in check["missing_documents"]:
        msgs.append(_("Documento mancante: %(desc)s") % {"desc": md["description"] or md["type"]})
    for me in check["missing_evidences"]:
        msgs.append(_("Evidenza mancante: %(desc)s") % {"desc": me["description"] or me["type"]})
    for ee in check["expired_evidences"]:
        msgs.append(
            _("Evidenza scaduta: %(title)s (scaduta il %(date)s)") % {
                "title": ee["title"],
                "date": ee["expired_on"],
            }
        )

    prefix = _("Requisiti parzialmente soddisfatti.") if suggested == "parziale" else _("Nessuna documentazione presente.")
    return (prefix + " " + "; ".join(msgs)) if msgs else prefix


class ControlInstanceViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ControlInstance.objects.select_related(
        "plant", "control__framework", "control__domain", "owner", "soa_approved_by"
    ).prefetch_related(
        "control__mappings_from__target_control__framework",
        "control__mappings_to__source_control__framework",
        "documents",
        "evidences",
        "assets",  # serializzato come M2M da fields="__all__": senza prefetch è 1 query/riga
    ).order_by("control__framework__code", "control__external_id")
    serializer_class = ControlInstanceSerializer
    permission_classes = [ControlInstancePermission]
    plant_field = "plant"

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from ..services import delete_control_instance

        instance = self.get_object()
        try:
            delete_control_instance(instance, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        qs        = super().get_queryset()
        plant_id  = self.request.query_params.get("plant")
        status    = self.request.query_params.get("status")
        framework = self.request.query_params.get("framework")

        if plant_id:
            qs = qs.filter(plant_id=plant_id)
            if not framework:
                from apps.plants.services import get_active_frameworks
                from apps.plants.models import Plant
                plant = Plant.objects.filter(pk=plant_id).first()
                if plant:
                    qs = qs.filter(control__framework__in=get_active_frameworks(plant))
                # Deduplication VH/base: se il plant ha sia il controllo base (L2)
                # che il corrispondente VH (L3) collegati da 'extends', mostra solo
                # la versione più specifica (VH) — valutare entrambi è ridondante.
                from ..models import ControlMapping
                plant_fw_ids = qs.values_list(
                    "control__framework_id", flat=True
                ).distinct()
                superseded_ids = ControlMapping.objects.filter(
                    relationship="extends",
                    source_control__framework_id__in=plant_fw_ids,
                    target_control__framework_id__in=plant_fw_ids,
                ).values_list("target_control_id", flat=True)
                if superseded_ids.exists():
                    qs = qs.exclude(control_id__in=superseded_ids)
        else:
            # Without plant filter, only return instances whose framework is actually
            # assigned to the plant (prevents showing orphaned instances as duplicates)
            from apps.plants.models import PlantFramework
            from django.db.models import OuterRef, Exists
            assigned = PlantFramework.objects.filter(
                plant=OuterRef("plant"),
                framework=OuterRef("control__framework"),
                deleted_at__isnull=True,
            )
            qs = qs.filter(Exists(assigned))
        if status:
            qs = qs.filter(status=status)
        if framework:
            qs = qs.filter(control__framework__code=framework)
        return qs

    @action(detail=True, methods=["post"])
    def propagate(self, request, pk=None):
        """
        Propaga lo stato ai controlli mappati dello stesso plant, rispettando
        tipo di relazione e direzione. La propagazione cross-plant è stata
        rimossa (ogni sito ha evidenze e controlli propri). (C4)
        """
        from ..services import propagate_control
        instance = self.get_object()
        result = propagate_control(instance, request.user)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        """
        Body: { "status": "compliant", "note": "..." }
        Chiama services.evaluate_control() — lancia 400 se mancano evidenze valide.
        """
        from ..services import evaluate_control
        from django.core.exceptions import ValidationError

        instance = self.get_object()
        new_status = request.data.get("status")
        note = request.data.get("note", "")
        if not new_status:
            from django.utils.translation import gettext as _
            return Response({"error": _("Campo 'status' obbligatorio.")}, status=400)
        try:
            evaluate_control(instance, new_status, request.user, note)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({"error": e.message}, status=400)

    @action(detail=True, methods=["get"], url_path="detail-info")
    def detail_info(self, request, pk=None):
        """
        Restituisce info complete per il drawer:
        descrizione, framework mappati, evidenze, storico valutazioni.
        """
        from django.utils import timezone
        from core.audit import AuditLog

        from django.utils import translation
        from apps.assets.models import Asset

        def _plant_assets(plant_id):
            return Asset.objects.filter(
                plant_id=plant_id, deleted_at__isnull=True
            ).only("id", "name", "asset_type").order_by("name")

        instance = self.get_object()
        lang = request.query_params.get("lang") or getattr(request, "LANGUAGE_CODE", None) or "it"
        control = instance.control

        mappings = list(
            control.mappings_from.select_related("target_control__framework").values(
                "target_control__framework__code",
                "target_control__external_id",
                "relationship",
            )
        )

        history = list(
            AuditLog.objects.filter(
                entity_type="controlinstance",
                entity_id=instance.pk,
                action_code="control.evaluated",
            )
            .order_by("-timestamp_utc")[:10]
            .values("timestamp_utc", "user_email_at_time", "payload")
        )

        today = timezone.localdate()
        current_evidences = [
            {
                "id": str(e.id),
                "title": e.title,
                "valid_until": str(e.valid_until) if e.valid_until else None,
                "expired": bool(e.valid_until and e.valid_until < today),
                "evidence_type": e.evidence_type,
            }
            for e in instance.evidences.all()
        ]

        linked_documents = [
            {
                "id": str(d.id),
                "document_code": d.document_code or "",
                "title": d.title,
                "document_type": d.document_type,
                "status": d.status,
                "review_due_date": str(d.review_due_date) if d.review_due_date else None,
            }
            for d in instance.documents.filter(deleted_at__isnull=True)
        ]

        from ..services import calc_suggested_status, check_evidence_requirements
        with translation.override(lang):
            requirements = check_evidence_requirements(instance, lang=lang)
        # riusa il check appena fatto: il flag `satisfied` non dipende dalla lingua
        suggested_status = calc_suggested_status(instance, check=requirements)

        with translation.override(lang):
            return Response({
                "current_status": instance.status,
                "suggested_status": suggested_status,
                "suggested_status_reason": _explain_suggestion(instance, suggested_status, requirements),
                "applicability": instance.applicability,
                "exclusion_justification": instance.exclusion_justification,
                "na_justification": instance.na_justification,
                "maturity_level": instance.maturity_level,
                "maturity_level_override": instance.maturity_level_override,
                "calc_maturity_level": instance.calc_maturity_level,
                "approved_in_soa": instance.approved_in_soa,
                "soa_approved_at": instance.soa_approved_at.isoformat() if instance.soa_approved_at else None,
                "soa_approved_by_name": (
                    (f"{instance.soa_approved_by.first_name} {instance.soa_approved_by.last_name}".strip()
                     or instance.soa_approved_by.email or instance.soa_approved_by.username)
                    if instance.soa_approved_by else None
                ),
                "needs_revaluation": instance.needs_revaluation,
                "needs_revaluation_since": str(instance.needs_revaluation_since) if instance.needs_revaluation_since else None,
                "notes": instance.notes,
                # Legame controllo↔asset (P1-5): asset collegati + asset disponibili
                # del plant, per popolare il M2M dalla UI e restringere la cascata change.
                "plant_id": str(instance.plant_id),
                "linked_assets": [
                    {"id": str(a.id), "name": a.name}
                    for a in instance.assets.filter(deleted_at__isnull=True)
                ],
                "available_assets": [
                    {"id": str(a.id), "name": a.name, "asset_type": a.asset_type}
                    for a in _plant_assets(instance.plant_id)
                ],
                "control_id": control.external_id,
                "control_uuid": str(control.pk),
                "title": control.get_title(lang),
                "domain": control.domain.get_name(lang) if control.domain else "",
                "framework": control.framework.code,
                "level": control.level,
                "control_category": control.control_category,
                "evidence_requirement": control.evidence_requirement,
                "description": control.tr("description", lang),
                "practical_summary": control.tr("practical_summary", lang),
                "implementation_guidance": control.tr("guidance", lang),
                "evidence_examples": control.tr("evidence_examples", lang, default=[]),
                "mappings": mappings,
                "evaluation_history": history,
                "current_evidences": current_evidences,
                "linked_documents": linked_documents,
                "requirements": requirements,
            })

    @action(detail=True, methods=["post"], url_path="link-document")
    def link_document(self, request, pk=None):
        """Collega un Document a questo ControlInstance."""
        from apps.documents.models import Document
        from django.utils.translation import gettext as _
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id, deleted_at__isnull=True)
            instance.documents.add(doc)
            return Response({"ok": True, "document_id": str(doc.id)})
        except Document.DoesNotExist:
            return Response({"error": _("Documento non trovato")}, status=404)

    @action(detail=True, methods=["post"], url_path="unlink-document")
    def unlink_document(self, request, pk=None):
        """Scollega un Document da questo ControlInstance."""
        from apps.documents.models import Document
        from django.utils.translation import gettext as _
        instance = self.get_object()
        doc_id = request.data.get("document_id")
        try:
            doc = Document.objects.get(pk=doc_id)
            instance.documents.remove(doc)
            return Response({"ok": True})
        except Document.DoesNotExist:
            return Response({"error": _("Documento non trovato")}, status=404)

    @action(detail=True, methods=["post"], url_path="link_evidence")
    def link_evidence(self, request, pk=None):
        from apps.documents.models import Evidence
        from django.utils.translation import gettext as _
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": _("Evidenza non trovata.")}, status=404)
        instance.evidences.add(evidence)
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="set-applicability")
    def set_applicability(self, request, pk=None):
        from ..services import validate_exclusion
        from django.core.exceptions import ValidationError
        instance = self.get_object()
        applicability = request.data.get("applicability", "applicabile")
        justification = request.data.get("justification", "")
        try:
            validate_exclusion(instance, applicability, justification, request.user)
            return Response({"ok": True, "applicability": applicability})
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=400)

    @action(detail=True, methods=["post"], url_path="set-maturity")
    def set_maturity(self, request, pk=None):
        """Override manuale del maturity level per VDA ISA TISAX."""
        from core.audit import log_action
        from django.utils.translation import gettext as _
        instance = self.get_object()
        level = request.data.get("maturity_level")
        if level is None or not (0 <= int(level) <= 5):
            return Response({"error": _("maturity_level deve essere tra 0 e 5")}, status=400)
        instance.maturity_level = int(level)
        instance.maturity_level_override = True
        instance.save(update_fields=["maturity_level", "maturity_level_override", "updated_at"])
        log_action(
            user=request.user,
            action_code="control.maturity_override",
            level="L2",
            entity=instance,
            payload={"maturity_level": int(level)},
        )
        return Response({"ok": True, "maturity_level": int(level)})

    @action(detail=False, methods=["post"], url_path="bulk-approve-soa")
    def bulk_approve_soa(self, request):
        """Approva (o revoca) formalmente un gruppo di ControlInstance per il SoA.

        Body: { "instance_ids": [...], "approved": true|false }
        Lo Statement of Applicability è un artefatto ISO 27001: l'approvazione è
        ammessa solo sui controlli di framework ISO (gli altri vengono ignorati).
        Con approved=false l'approvazione viene revocata (azzera chi/quando). (C5)
        """
        from django.utils import timezone
        from core.audit import log_action
        ids = request.data.get("instance_ids", [])
        approved = bool(request.data.get("approved", True))
        qs = self.get_queryset().filter(
            pk__in=ids, control__framework__code__icontains="ISO"
        )
        instances = list(qs)  # materializza prima dell'update (poi i filtri non matchano più)
        now = timezone.now()
        if approved:
            qs.update(approved_in_soa=True, soa_approved_at=now, soa_approved_by=request.user)
        else:
            qs.update(approved_in_soa=False, soa_approved_at=None, soa_approved_by=None)
        for instance in instances:
            log_action(
                user=request.user,
                action_code="control.soa_approved" if approved else "control.soa_revoked",
                level="L1",
                entity=instance,
                payload={"framework": instance.control.framework.code, "approved": approved},
            )
        return Response({"ok": True, "approved_count": len(instances), "approved": approved})

    @action(detail=True, methods=["post"], url_path="apply-suggestion")
    def apply_suggestion(self, request, pk=None):
        """Valuta il controllo applicando lo stato suggerito dal sistema."""
        from ..services import calc_suggested_status, evaluate_control
        from django.core.exceptions import ValidationError

        instance = self.get_object()
        suggested = calc_suggested_status(instance)
        note = request.data.get("note", "")
        try:
            evaluate_control(instance, suggested, request.user, note)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({"error": e.message}, status=400)

    @action(detail=True, methods=["post"], url_path="unlink_evidence")
    def unlink_evidence(self, request, pk=None):
        from apps.documents.models import Evidence
        from django.utils.translation import gettext as _
        instance = self.get_object()
        evidence_id = request.data.get("evidence_id")
        try:
            evidence = Evidence.objects.get(pk=evidence_id)
        except Evidence.DoesNotExist:
            return Response({"error": _("Evidenza non trovata.")}, status=404)
        instance.evidences.remove(evidence)
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="needs-revaluation")
    def needs_revaluation_list(self, request):
        """Controlli che richiedono rivalutazione dopo un change."""
        plant_id = request.query_params.get("plant")
        qs = self.get_queryset().filter(needs_revaluation=True)
        if plant_id:
            qs = qs.filter(plant_id=plant_id)
        return Response(self.get_serializer(qs, many=True).data)
