import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action
from core.viewsets import SoftDeleteAuditMixin
from .models import CommitteeMeeting, DocumentWorkflowPolicy, RoleAssignment, SecurityCommittee
from .permissions import GovernancePermission
from .serializers import (
    CommitteeMeetingSerializer,
    DocumentWorkflowPolicySerializer,
    RoleAssignmentSerializer,
    SecurityCommitteeSerializer,
)


class RoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.select_related("user").all()
    serializer_class = RoleAssignmentSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        # Scoping per accesso plant (D1): un utente non org-scope non deve
        # leggere i titolari (con PII) dei siti a cui non ha accesso.
        from .services import visible_role_assignments
        return visible_role_assignments(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="governance.role_assignment.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete di una assegnazione di ruolo, con audit trail.
        Usare per pulizia dati / test, non per la gestione ordinaria (dove si usa 'termina' o 'sostituisci').
        """
        instance = self.get_object()
        instance.soft_delete()
        log_action(
            user=request.user,
            action_code="governance.role_assignment.delete",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id)},
        )
        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="termina")
    def termina(self, request, pk=None):
        """Termina un ruolo impostando valid_until."""
        from .services import terminate_role
        from dateutil import parser as dateparser

        assignment = self.get_object()

        if assignment.valid_until and assignment.valid_until < timezone.localdate():
            return Response({"error": _("Questo ruolo è già terminato.")}, status=400)

        reason = request.data.get("reason", "")
        if not reason or len(reason.strip()) < 5:
            return Response(
                {"error": _("Motivo terminazione obbligatorio (min 5 caratteri).")},
                status=400,
            )

        termination_date = None
        date_str = request.data.get("termination_date")
        if date_str:
            try:
                termination_date = dateparser.parse(date_str).date()
            except (ValueError, TypeError, OverflowError) as exc:
                logging.getLogger(__name__).warning("governance: termination_date non valida ignorata: %s", exc)

        assignment = terminate_role(assignment, request.user, termination_date, reason)
        return Response({
            "ok":          True,
            "valid_until": str(assignment.valid_until),
            "message":     f"Ruolo terminato il {assignment.valid_until}",
        })

    @action(detail=True, methods=["post"], url_path="sostituisci")
    def sostituisci(self, request, pk=None):
        """Successione atomica: termina questo ruolo e lo assegna al nuovo utente."""
        from django.contrib.auth import get_user_model
        from .services import replace_role
        from dateutil import parser as dateparser

        assignment  = self.get_object()
        User        = get_user_model()
        new_user_id = request.data.get("new_user_id")
        reason      = request.data.get("reason", "")

        if not new_user_id:
            return Response({"error": _("new_user_id obbligatorio.")}, status=400)
        new_user = User.objects.filter(pk=new_user_id).first()
        if not new_user:
            return Response({"error": _("Utente non trovato.")}, status=404)

        handover_date = None
        date_str = request.data.get("handover_date")
        if date_str:
            try:
                handover_date = dateparser.parse(date_str).date()
            except (ValueError, TypeError, OverflowError) as exc:
                logging.getLogger(__name__).warning("governance: handover_date non valida ignorata: %s", exc)

        old_a, new_a = replace_role(
            assignment, new_user, request.user,
            handover_date=handover_date,
            reason=reason,
            document_id=request.data.get("document_id"),
        )
        return Response({
            "ok":             True,
            "old_assignment": str(old_a.pk),
            "new_assignment": str(new_a.pk),
            "handover_date":  str(new_a.valid_from),
            "new_user":       new_user.get_full_name() or new_user.email,
            "message": (
                f"Ruolo {new_a.role} passato a "
                f"{new_user.get_full_name() or new_user.email} "
                f"dal {new_a.valid_from}"
            ),
        })

    @action(detail=False, methods=["get"], url_path="vacanti")
    def vacanti(self, request):
        """Ruoli obbligatori senza titolare attivo."""
        from .services import get_vacant_mandatory_roles
        from apps.plants.models import Plant

        plant_id = request.query_params.get("plant")
        # Vacanze calcolate direttamente dal plant richiesto: serve accesso al
        # sito; senza plant la vista è org-wide (soli nomi ruolo, nessun dato
        # di sito) → nessun vincolo aggiuntivo (sweep 2026-06-12).
        from core.scoping import require_plant_access
        require_plant_access(request.user, plant_id or None, aggregate_requires_org=False)
        plant    = Plant.objects.filter(pk=plant_id).first() if plant_id else None
        vacant   = get_vacant_mandatory_roles(plant)
        return Response({
            "vacant_roles": vacant,
            "count":        len(vacant),
            "critical":     len(vacant) > 0,
        })

    @action(detail=False, methods=["get"], url_path="in-scadenza")
    def in_scadenza(self, request):
        """Ruoli in scadenza nei prossimi N giorni o già scaduti."""
        from .services import get_expiring_roles, visible_role_assignments

        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(0, min(days, 365))
        result = get_expiring_roles(days)
        # Stesso scoping plant della lista (D1).
        result = {
            "expiring": visible_role_assignments(result["expiring"], request.user),
            "expired":  visible_role_assignments(result["expired"], request.user),
        }
        today  = timezone.localdate()

        return Response({
            "expiring": [
                {
                    "id":          str(a.pk),
                    "role":        a.role,
                    "user":        a.user.get_full_name() or a.user.email,
                    "valid_until": str(a.valid_until),
                    "days_left":   (a.valid_until - today).days,
                }
                for a in result["expiring"]
            ],
            "expired": [
                {
                    "id":          str(a.pk),
                    "role":        a.role,
                    "user":        a.user.get_full_name() or a.user.email,
                    "valid_until": str(a.valid_until),
                }
                for a in result["expired"]
            ],
        })


class DocumentWorkflowPolicyViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    """
    ViewSet per configurare da Governance il workflow documentale M07.

    La policy governa CHI può inviare/revisionare/approvare i documenti: ogni
    modifica (create/update/delete) è materia di controllo → audit completo.
    """

    queryset = DocumentWorkflowPolicy.objects.all()
    serializer_class = DocumentWorkflowPolicySerializer
    permission_classes = [GovernancePermission]
    audit_action = "governance.document_workflow_policy"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="governance.document_workflow_policy.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "document_type": instance.document_type},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="governance.document_workflow_policy.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "document_type": instance.document_type},
        )


class SecurityCommitteeViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    queryset = SecurityCommittee.objects.all()
    serializer_class = SecurityCommitteeSerializer
    permission_classes = [GovernancePermission]
    audit_action = "governance.security_committee"


class CommitteeMeetingViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    queryset = CommitteeMeeting.objects.all()
    serializer_class = CommitteeMeetingSerializer
    permission_classes = [GovernancePermission]
    audit_action = "governance.committee_meeting"
