import logging

from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.utils import timezone
from django.utils.translation import gettext as _

from core.audit import log_action
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin
from .models import (
    DocumentWorkflowPolicy,
    RoleAssignment,
    RoleRequirement,
    CommitteeMember,
    SecurityCommittee,
    SecurityObjective,
)
from .permissions import GovernancePermission, SecurityObjectivePermission
from .serializers import (
    CommitteeMemberSerializer,
    DocumentWorkflowPolicySerializer,
    RoleAssignmentSerializer,
    RoleRequirementSerializer,
    SecurityCommitteeSerializer,
    SecurityObjectiveMeasurementSerializer,
    SecurityObjectiveSerializer,
)


class RoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.select_related("user").all()
    serializer_class = RoleAssignmentSerializer
    permission_classes = [GovernancePermission]
    filterset_fields = ["user", "role", "scope_type"]

    def get_queryset(self):
        # Scoping per accesso plant (D1): un utente non org-scope non deve
        # leggere i titolari (con PII) dei siti a cui non ha accesso.
        from .services import visible_role_assignments
        return visible_role_assignments(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from .services import create_role_assignment

        try:
            serializer.instance = create_role_assignment(serializer.validated_data, self.request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict) from None

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

        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            old_a, new_a = replace_role(
                assignment, new_user, request.user,
                handover_date=handover_date,
                reason=reason,
                document_id=request.data.get("document_id"),
            )
        except DjangoValidationError as exc:
            return Response({"error": " ".join(exc.messages)}, status=400)
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

    @action(detail=False, methods=["get"], url_path="coverage-matrix")
    def coverage_matrix(self, request):
        """Matrice di copertura dei ruoli obbligatori per scope (org + per-sito).

        Lo scoping plant è gestito da ``get_role_coverage_matrix`` (mostra solo i
        siti accessibili all'utente).
        """
        from .services import get_role_coverage_matrix

        try:
            days = int(request.query_params.get("expiring_days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(0, min(days, 365))
        return Response(get_role_coverage_matrix(request.user, expiring_days=days))

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


def _django_to_drf(exc):
    from rest_framework.exceptions import ValidationError as DRFValidationError

    return DRFValidationError(getattr(exc, "message_dict", None) or exc.messages)


class SecurityCommitteeViewSet(viewsets.ModelViewSet):
    """Organi di governo (CdA, comitato sicurezza, direzione) con i componenti.

    Lettura filtrata per perimetro: i componenti sono dati personali. Scrittura
    a governance (super_admin/compliance_officer) e solo su organi il cui
    perimetro è interamente accessibile (controllo nei services).
    """

    queryset = SecurityCommittee.objects.prefetch_related(
        "plants",
        Prefetch("members", queryset=CommitteeMember.objects.select_related("user")),
    )
    serializer_class = SecurityCommitteeSerializer
    permission_classes = [GovernancePermission]
    filterset_fields = ["committee_type"]

    def get_queryset(self):
        from .services import visible_committees

        return visible_committees(super().get_queryset(), self.request.user)

    def handle_exception(self, exc):
        from django.core.exceptions import ValidationError as DjangoValidationError

        if isinstance(exc, DjangoValidationError):
            exc = _django_to_drf(exc)
        return super().handle_exception(exc)

    def perform_create(self, serializer):
        from .services import create_committee

        create_committee(serializer, self.request.user)

    def perform_update(self, serializer):
        from .services import update_committee

        update_committee(serializer, self.request.user)

    def perform_destroy(self, instance):
        from .services import delete_committee

        delete_committee(instance, self.request.user)


class CommitteeMemberViewSet(viewsets.ModelViewSet):
    """Componenti degli organi di governo. Si vedono solo quelli degli organi
    visibili; chi lascia la carica si chiude con `valid_until`."""

    queryset = CommitteeMember.objects.select_related("user", "committee").filter(
        committee__deleted_at__isnull=True
    )
    serializer_class = CommitteeMemberSerializer
    permission_classes = [GovernancePermission]
    filterset_fields = ["committee", "body_role"]

    def get_queryset(self):
        from .services import visible_committees

        visible = visible_committees(SecurityCommittee.objects.all(), self.request.user)
        return super().get_queryset().filter(committee__in=visible.values("id"))

    def handle_exception(self, exc):
        from django.core.exceptions import ValidationError as DjangoValidationError

        if isinstance(exc, DjangoValidationError):
            exc = _django_to_drf(exc)
        return super().handle_exception(exc)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        from .services import create_member, visible_committees

        committee = serializer.validated_data["committee"]
        if not visible_committees(SecurityCommittee.objects.filter(pk=committee.pk), self.request.user).exists():
            raise PermissionDenied(_("Accesso negato per questo organo."))
        create_member(serializer, self.request.user)

    def perform_update(self, serializer):
        from .services import update_member

        update_member(serializer, self.request.user)

    def perform_destroy(self, instance):
        from .services import delete_member

        delete_member(instance, self.request.user)


class RoleRequirementViewSet(SoftDeleteAuditMixin, viewsets.ModelViewSet):
    """Configura QUALI ruoli sono obbligatori e a quale scope (alimenta la
    matrice di copertura). Materia di governance → scrittura solo
    super_admin/compliance_officer, ogni modifica è auditata."""

    queryset = RoleRequirement.objects.all()
    serializer_class = RoleRequirementSerializer
    permission_classes = [GovernancePermission]
    filterset_fields = ["role", "scope_level", "enabled"]
    audit_action = "governance.role_requirement"

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action_code="governance.role_requirement.create",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "role": instance.role, "scope_level": instance.scope_level},
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            user=self.request.user,
            action_code="governance.role_requirement.update",
            level="L2",
            entity=instance,
            payload={"id": str(instance.id), "role": instance.role, "enabled": instance.enabled},
        )


class SecurityObjectiveViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Obiettivi di sicurezza delle informazioni (ISO/IEC 27001 §6.2).

    Gli obiettivi di organizzazione (`plant=null`) sono visibili a tutti:
    sono impegni aziendali, non dati di un singolo sito.
    """

    queryset = SecurityObjective.objects.select_related("plant", "kpi_definition").all()
    serializer_class = SecurityObjectiveSerializer
    permission_classes = [SecurityObjectivePermission]
    filterset_fields = ["plant", "status", "origin", "measure_source", "owner_role"]
    audit_action = "governance.security_objective"
    allow_null_plant = True

    def handle_exception(self, exc):
        # I services sollevano la ValidationError di Django (sono chiamabili
        # anche fuori da DRF): qui diventa una 400 con i campi, non una 500.
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        if isinstance(exc, DjangoValidationError):
            exc = DRFValidationError(getattr(exc, "message_dict", None) or exc.messages)
        return super().handle_exception(exc)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.action == "list":
            # Valori correnti di tutta la pagina in due query, invece di due
            # per riga (regola #6).
            from .services import latest_objective_values

            ctx["objective_values"] = latest_objective_values(
                self.filter_queryset(self.get_queryset())
            )
        return ctx

    def perform_create(self, serializer):
        from .services import create_objective

        create_objective(serializer, self.request.user)

    def perform_update(self, serializer):
        from .services import update_objective

        update_objective(serializer, self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        from .services import activate_objective

        objective = activate_objective(self.get_object(), request.user)
        return Response(self.get_serializer(objective).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        from .services import suspend_objective

        objective = suspend_objective(
            self.get_object(), request.user, note=request.data.get("note", "")
        )
        return Response(self.get_serializer(objective).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .services import close_objective

        objective = close_objective(
            self.get_object(),
            request.user,
            outcome=request.data.get("outcome", ""),
            note=request.data.get("note", ""),
        )
        return Response(self.get_serializer(objective).data)

    @action(detail=True, methods=["post"])
    def measure(self, request, pk=None):
        from .services import record_objective_measurement

        measurement = record_objective_measurement(
            self.get_object(),
            request.user,
            value=request.data.get("value"),
            measured_on=request.data.get("measured_on") or None,
            note=request.data.get("note", ""),
        )
        return Response(SecurityObjectiveMeasurementSerializer(measurement).data, status=201)

    @action(detail=True, methods=["get"])
    def series(self, request, pk=None):
        """Serie storica delle misure, qualunque sia la sorgente."""
        from .services import objective_series

        return Response({"items": objective_series(self.get_object())})

    @action(detail=False, methods=["get"])
    def overview(self, request):
        from .services import objectives_overview

        return Response(objectives_overview(self.filter_queryset(self.get_queryset())))
