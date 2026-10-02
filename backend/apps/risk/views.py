from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from core.audit import log_action
from core.jwt import ExportRateThrottle
from core.scoping import PlantScopedQuerysetMixin
from core.viewsets import SoftDeleteAuditMixin

from . import services
from .models import (
    InformationClass,
    RiskAcceptance,
    RiskAssessment,
    RiskAssessmentCycle,
    RiskExistingMeasure,
    RiskGovernancePolicy,
    RiskLocalImpactReport,
    RiskMitigationPlan,
    ThreatCatalogEntry,
)
from .permissions import RiskGovernancePermission, RiskPermission
from .serializers import (
    InformationClassSerializer,
    RiskAcceptanceSerializer,
    RiskAssessmentCycleSerializer,
    RiskAssessmentSerializer,
    RiskEvaluationInputSerializer,
    RiskExistingMeasureSerializer,
    RiskGovernancePolicySerializer,
    RiskLocalImpactReportSerializer,
    RiskMitigationPlanSerializer,
    ThreatCatalogEntrySerializer,
)


def _call_service(fn, *args, **kwargs):
    """Esegue un service traducendo la ValidationError Django in 400 DRF."""
    try:
        return fn(*args, **kwargs)
    except DjangoValidationError as exc:
        raise DRFValidationError({"error": exc.messages[0]}) from exc


def _plant_from_param(request, value):
    """Risolve un id di sito dal body/query (None = registro di gruppo)."""
    from apps.plants.models import Plant

    if value in (None, "", "null"):
        return None
    plant = Plant.objects.filter(pk=value).first()
    if plant is None:
        raise DRFValidationError({"plant": _("Sito inesistente.")})
    return plant


def _evaluation_data(request, partial: bool):
    serializer = RiskEvaluationInputSerializer(data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class RiskAssessmentViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Registro dei rischi.

    Filtri: `plant=<id>` (registro del sito; `include_inherited=1` aggiunge i
    rischi di gruppo ereditati) o `plant=null` (registro di gruppo);
    `legacy=1` mostra la valutazione precedente (metodo superato).
    """

    queryset = RiskAssessment.objects.select_related(
        "plant", "cycle", "asset", "supplier", "critical_process", "threat",
        "owner", "treatment_owner", "assessed_by",
    ).prefetch_related(
        "information_classes", "affected_plants",
        Prefetch("mitigation_plans", queryset=RiskMitigationPlan.objects.all()),
        Prefetch("acceptances", queryset=RiskAcceptance.objects.all()),
    )
    serializer_class = RiskAssessmentSerializer
    permission_classes = [RiskPermission]
    plant_field = "plant"
    allow_null_plant = True

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        plant = self.request.query_params.get("plant")
        ctx["register_plant"] = plant if plant not in (None, "", "null") else None
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("legacy") == "1":
            qs = qs.filter(cycle__kind="legacy")
        elif self.action != "retrieve":
            # La scheda (retrieve) apre anche i rischi del metodo superato, in sola
            # lettura; scritture e azioni li rifiutano (services.is_legacy).
            qs = qs.exclude(cycle__kind="legacy")
        plant = params.get("plant")
        if plant == "null":
            qs = qs.filter(plant__isnull=True)
        elif plant:
            q = Q(plant_id=plant)
            if params.get("include_inherited") == "1":
                q |= Q(plant__isnull=True, affected_plants=plant)
            qs = qs.filter(q).distinct()
        for field in ("status", "asset_type", "treatment", "current_class", "owner"):
            if params.get(field):
                qs = qs.filter(**{field: params[field]})
        if params.get("applicable") in ("true", "false"):
            qs = qs.filter(applicable=params["applicable"] == "true")
        if params.get("untreated_high") == "1":
            qs = services.untreated_high_risks(qs.filter(applicable=True, status="completato"))
        return qs.order_by("asset_type", "threat__code", "created_at")

    def create(self, request, *args, **kwargs):
        plant = _plant_from_param(request, request.data.get("plant"))
        risk = _call_service(services.create_risk, request.user, plant, _evaluation_data(request, False))
        return Response(self.get_serializer(risk).data, status=201)

    def update(self, request, *args, **kwargs):
        risk = self.get_object()
        risk = _call_service(services.update_risk, request.user, risk, _evaluation_data(request, True))
        return Response(self.get_serializer(risk).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        _call_service(services.delete_risk, request.user, self.get_object())
        return Response(status=204)

    def _risk_action(self, fn, *args, **kwargs):
        risk = _call_service(fn, self.request.user, self.get_object(), *args, **kwargs)
        return Response(self.get_serializer(risk).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._risk_action(services.complete_risk)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._risk_action(services.confirm_risk)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._risk_action(services.reopen_risk)

    @action(detail=True, methods=["post"], url_path="apply-expected")
    def apply_expected(self, request, pk=None):
        return self._risk_action(services.apply_expected_risk, request.data.get("note", ""))

    @action(detail=True, methods=["get"], url_path="completeness")
    def completeness(self, request, pk=None):
        risk = self.get_object()
        services.recompute_risk(risk)
        return Response({"errors": services.risk_completeness_errors(risk)})

    @action(detail=True, methods=["get"], url_path="acceptance-requirements")
    def acceptance_requirements(self, request, pk=None):
        return Response(services.acceptance_requirements(self.get_object()))

    @action(detail=False, methods=["post"], url_path="not-applicable")
    def not_applicable(self, request):
        """Body: {plant: id|null, asset_type, threat, reason}."""
        plant = _plant_from_param(request, request.data.get("plant"))
        threat = ThreatCatalogEntry.objects.filter(pk=request.data.get("threat")).first()
        if threat is None:
            raise DRFValidationError({"threat": _("Minaccia inesistente.")})
        risk = _call_service(
            services.mark_not_applicable, request.user, plant,
            request.data.get("asset_type", ""), threat, request.data.get("reason", ""),
        )
        return Response(self.get_serializer(risk).data, status=201)

    def _register_plant(self, request):
        from core.scoping import require_plant_access

        plant = _plant_from_param(request, request.query_params.get("plant"))
        require_plant_access(request.user, plant, aggregate_requires_org=False)
        return plant

    @action(detail=False, methods=["get"])
    def coverage(self, request):
        return Response(services.register_coverage(self._register_plant(request)))

    @action(detail=False, methods=["get"])
    def attention(self, request):
        """Contatori di cosa richiede di agire nel registro, con i rischi coinvolti."""
        return Response(services.register_attention(self._register_plant(request)))

    @action(detail=False, methods=["get"])
    def triggers(self, request):
        return Response(services.revaluation_triggers(self._register_plant(request)))

    @action(detail=False, methods=["get"])
    def matrix(self, request):
        """Conteggi per cella della matrice, attuale o atteso (`?view=expected`)."""
        plant = self._register_plant(request)
        expected = request.query_params.get("view") == "expected"
        p_field, i_field = ("expected_probability", "expected_impact") if expected else ("probability", "impact")
        rows = services.register_queryset(plant, include_inherited=plant is not None).filter(
            applicable=True, status="completato",
        ).values_list(p_field, i_field)
        counts: dict = {}
        for p, i in rows:
            if p and i:
                counts[(p, i)] = counts.get((p, i), 0) + 1
        return Response([
            {"probability": p, "impact": i, "count": counts.get((p, i), 0), "class": services.risk_class(p, i)}
            for p in range(5, 0, -1) for i in range(1, 6)
        ])

    @action(detail=True, methods=["get"], url_path="context")
    def context(self, request, pk=None):
        return Response(services.get_risk_bia_bcp_context(self.get_object()))

    @action(detail=False, methods=["get"], url_path="export", throttle_classes=[ExportRateThrottle])
    def export(self, request):
        """Excel del registro corrente del sito (`plant`) o del gruppo (`plant=null`)."""
        from django.http import HttpResponse

        plant = self._register_plant(request)
        excel_bytes = services.generate_risk_excel(plant)
        log_action(
            user=request.user, action_code="risk.register.export", level="L2",
            entity=plant if plant is not None else request.user,
            payload={"plant_id": str(plant.pk) if plant else None},
        )
        label = plant.code if plant is not None else "gruppo"
        response = HttpResponse(
            excel_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="risk_register_{label}.xlsx"'
        return response


class RiskExistingMeasureViewSet(viewsets.ModelViewSet):
    """Misure esistenti di un rischio (`?risk=<id>`)."""

    serializer_class = RiskExistingMeasureSerializer
    permission_classes = [RiskPermission]

    def get_queryset(self):
        from core.scoping import scope_queryset_by_plant

        qs = RiskExistingMeasure.objects.select_related("risk", "control_instance__control")
        qs = scope_queryset_by_plant(qs, self.request.user, plant_field="risk__plant", allow_null_plant=True)
        if self.request.query_params.get("risk"):
            qs = qs.filter(risk_id=self.request.query_params["risk"])
        return qs

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        risk = data.pop("risk")
        serializer.instance = _call_service(services.save_existing_measure, self.request.user, risk, data)

    def perform_update(self, serializer):
        data = dict(serializer.validated_data)
        data.pop("risk", None)
        serializer.instance = _call_service(
            services.save_existing_measure, self.request.user, serializer.instance.risk, data, serializer.instance,
        )

    def perform_destroy(self, instance):
        _call_service(services.delete_existing_measure, self.request.user, instance)


class RiskMitigationPlanViewSet(viewsets.ModelViewSet):
    """Piani di trattamento (`?assessment=<id>` o `?plant=<id>`)."""

    serializer_class = RiskMitigationPlanSerializer
    permission_classes = [RiskPermission]

    def get_queryset(self):
        from core.scoping import scope_queryset_by_plant

        params = self.request.query_params
        qs = RiskMitigationPlan.objects.select_related(
            "assessment", "owner", "verified_by", "bcp_plan", "control_instance__control",
        )
        if params.get("legacy") == "1":
            qs = qs.filter(assessment__cycle__kind="legacy")
        else:
            qs = qs.exclude(assessment__cycle__kind="legacy")
        qs = scope_queryset_by_plant(qs, self.request.user, plant_field="assessment__plant", allow_null_plant=True)
        if params.get("assessment"):
            qs = qs.filter(assessment_id=params["assessment"])
        if params.get("plant") == "null":
            qs = qs.filter(assessment__plant__isnull=True)
        elif params.get("plant"):
            qs = qs.filter(assessment__plant_id=params["plant"])
        if params.get("open") == "1":
            qs = qs.filter(completed_at__isnull=True)
        return qs.order_by("due_date")

    def perform_create(self, serializer):
        risk = serializer.validated_data["assessment"]
        _call_service(services.require_plan_write, self.request.user, risk)
        with transaction.atomic():
            instance = serializer.save(created_by=self.request.user)
            log_action(user=self.request.user, action_code="risk.mitigation_plan.create", level="L2",
                       entity=instance, payload={"risk_id": str(risk.pk)})

    def perform_update(self, serializer):
        _call_service(services.require_plan_write, self.request.user, serializer.instance.assessment)
        was_completed = serializer.instance.completed_at
        with transaction.atomic():
            instance = serializer.save()
            # Riaprire o ricompletare una misura annulla la verifica di efficacia.
            if instance.completed_at != was_completed and instance.verified_at:
                instance.verified_at = None
                instance.verified_by = None
                instance.save(update_fields=["verified_at", "verified_by", "updated_at"])
            log_action(user=self.request.user, action_code="risk.mitigation_plan.update", level="L2",
                       entity=instance, payload={"completed": bool(instance.completed_at)})

    def perform_destroy(self, instance):
        _call_service(services.require_plan_write, self.request.user, instance.assessment)
        with transaction.atomic():
            instance.soft_delete()
            log_action(user=self.request.user, action_code="risk.mitigation_plan.deleted", level="L2",
                       entity=instance, payload={"risk_id": str(instance.assessment_id)})

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        plan = _call_service(services.verify_mitigation_plan, request.user, self.get_object(),
                             request.data.get("note", ""))
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def uncomplete(self, request, pk=None):
        """Annulla il completamento segnato per errore (e la verifica)."""
        plan = self.get_object()
        _call_service(services.require_plan_write, request.user, plan.assessment)
        if not plan.completed_at:
            raise DRFValidationError({"error": _("Il piano non è ancora completato.")})
        with transaction.atomic():
            plan.completed_at = None
            plan.verified_at = None
            plan.verified_by = None
            plan.save(update_fields=["completed_at", "verified_at", "verified_by", "updated_at"])
            log_action(user=request.user, action_code="risk.mitigation_plan.uncomplete", level="L2",
                       entity=plan, payload={"risk_id": str(plan.assessment_id)})
        return Response(self.get_serializer(plan).data)


class RiskAcceptanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Accettazioni (`?risk=`, `?status=`, `?plant=`, `?awaiting_me=1`)."""

    serializer_class = RiskAcceptanceSerializer
    permission_classes = [RiskPermission]

    def get_queryset(self):
        from core.scoping import scope_queryset_by_plant

        qs = RiskAcceptance.objects.select_related("risk", "risk__plant", "risk__threat", "body", "opinion_by")
        qs = scope_queryset_by_plant(qs, self.request.user, plant_field="risk__plant", allow_null_plant=True)
        params = self.request.query_params
        if params.get("risk"):
            qs = qs.filter(risk_id=params["risk"])
        if params.get("status"):
            qs = qs.filter(status__in=params["status"].split(","))
        if params.get("plant") == "null":
            qs = qs.filter(risk__plant__isnull=True)
        elif params.get("plant"):
            qs = qs.filter(risk__plant_id=params["plant"])
        qs = qs.order_by("-created_at")
        if params.get("awaiting_me") == "1":
            user = self.request.user
            opinion = services.can_give_opinion(user)
            ids = [
                a.pk for a in qs.filter(status="pending")
                if services.signable_roles(user, a) or (opinion and a.upper_opinion == "pending")
            ]
            qs = qs.filter(pk__in=ids)
        return qs

    def create(self, request, *args, **kwargs):
        """Richiesta di accettazione. Body: {risk, rationale, expires_on?, body?, body_resolution_ref?}."""
        from apps.governance.models import SecurityCommittee

        risk = RiskAssessment.objects.filter(pk=request.data.get("risk")).first()
        if risk is None or not self._can_see(risk):
            raise DRFValidationError({"risk": _("Rischio inesistente.")})
        body = SecurityCommittee.objects.filter(pk=request.data.get("body")).first() if request.data.get("body") else None
        acc = _call_service(
            services.request_acceptance, request.user, risk,
            rationale=request.data.get("rationale", ""),
            expires_on=self._date(request.data.get("expires_on")),
            body=body, body_resolution_ref=request.data.get("body_resolution_ref", ""),
        )
        return Response(self.get_serializer(acc).data, status=201)

    def _can_see(self, risk):
        from core.scoping import user_can_access_plant, user_has_org_scope

        user = self.request.user
        return user_has_org_scope(user) if risk.plant_id is None else user_can_access_plant(user, risk.plant_id)

    @staticmethod
    def _date(value):
        import datetime

        if not value:
            return None
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError as exc:
            raise DRFValidationError({"expires_on": _("Data non valida.")}) from exc

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        acc = _call_service(services.sign_acceptance, request.user, self.get_object())
        return Response(self.get_serializer(acc).data)

    @action(detail=True, methods=["post"])
    def opinion(self, request, pk=None):
        acc = _call_service(
            services.give_opinion, request.user, self.get_object(),
            favorable=bool(request.data.get("favorable")), note=request.data.get("note", ""),
        )
        return Response(self.get_serializer(acc).data)

    @action(detail=True, methods=["post"], url_path="body-decision")
    def body_decision(self, request, pk=None):
        from apps.governance.models import SecurityCommittee

        body = SecurityCommittee.objects.filter(pk=request.data.get("body")).first()
        acc = _call_service(
            services.record_body_decision, request.user, self.get_object(),
            body=body, resolution_ref=request.data.get("resolution_ref", ""),
        )
        return Response(self.get_serializer(acc).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        acc = _call_service(services.revoke_acceptance, request.user, self.get_object(), request.data.get("reason", ""))
        return Response(self.get_serializer(acc).data)


class RiskLocalImpactReportViewSet(viewsets.ReadOnlyModelViewSet):
    """Segnalazioni d'impatto locale sui rischi di gruppo ereditati."""

    serializer_class = RiskLocalImpactReportSerializer
    permission_classes = [RiskPermission]

    def get_queryset(self):
        from core.scoping import scope_queryset_by_plant

        qs = RiskLocalImpactReport.objects.select_related("risk", "risk__threat", "plant")
        qs = scope_queryset_by_plant(qs, self.request.user, plant_field="plant")
        params = self.request.query_params
        if params.get("risk"):
            qs = qs.filter(risk_id=params["risk"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs

    def create(self, request, *args, **kwargs):
        risk = RiskAssessment.objects.filter(pk=request.data.get("risk"), plant__isnull=True).first()
        plant = _plant_from_param(request, request.data.get("plant"))
        if risk is None or plant is None:
            raise DRFValidationError({"error": _("Indica il rischio di gruppo e il sito.")})
        try:
            impact = int(request.data.get("local_impact"))
        except (TypeError, ValueError):
            impact = 0
        report = _call_service(services.report_local_impact, request.user, risk, plant,
                               local_impact=impact, note=request.data.get("note", ""))
        return Response(self.get_serializer(report).data, status=201)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        report = _call_service(services.acknowledge_local_impact, request.user, self.get_object())
        return Response(self.get_serializer(report).data)


class ThreatCatalogViewSet(viewsets.ModelViewSet):
    """Catalogo minacce: voci di gruppo (sola lettura) e voci personalizzate."""

    queryset = ThreatCatalogEntry.objects.all()
    serializer_class = ThreatCatalogEntrySerializer
    permission_classes = [RiskGovernancePermission]

    def get_queryset(self):
        from django.db.models import Q, TextField
        from django.db.models.functions import Cast

        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("asset_type"):
            qs = qs.filter(asset_types__contains=[params["asset_type"]])
        if params.get("source"):
            qs = qs.filter(source=params["source"])
        if params.get("active", "true") != "all":
            qs = qs.filter(active=params.get("active", "true") == "true")
        if params.get("q"):
            q = params["q"]
            qs = qs.annotate(_tr=Cast("translations", TextField())).filter(
                Q(code__icontains=q) | Q(_tr__icontains=q)
            )
        return qs

    def create(self, request, *args, **kwargs):
        from .services import create_custom_threat

        data = request.data
        entry = _call_service(
            create_custom_threat, request.user,
            code=data.get("code"), asset_types=data.get("asset_types"),
            cia=data.get("cia", []), translations=data.get("translations", {}),
        )
        return Response(self.get_serializer(entry).data, status=201)

    def update(self, request, *args, **kwargs):
        from .services import update_custom_threat

        entry = self.get_object()
        fields = {k: request.data[k] for k in ("asset_types", "cia", "translations", "active") if k in request.data}
        entry = _call_service(update_custom_threat, request.user, entry, **fields)
        return Response(self.get_serializer(entry).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        from .services import deactivate_threat

        _call_service(deactivate_threat, request.user, self.get_object())
        return Response(status=204)


class InformationClassViewSet(SoftDeleteAuditMixin, PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Classi di informazioni per sito; senza sito = classi di gruppo."""

    queryset = InformationClass.objects.select_related("plant", "owner").prefetch_related("critical_processes")
    serializer_class = InformationClassSerializer
    permission_classes = [RiskPermission]
    plant_field = "plant"
    allow_null_plant = True
    audit_action = "risk.information_class"

    def get_queryset(self):
        qs = super().get_queryset()
        plant = self.request.query_params.get("plant")
        if plant == "null":
            qs = qs.filter(plant__isnull=True)
        elif plant:
            qs = qs.filter(plant_id=plant)
        return qs

    def perform_create(self, serializer):
        from core.scoping import require_org_scope_for_org_wide

        require_org_scope_for_org_wide(self.request.user, serializer.validated_data.get("plant"))
        instance = serializer.save(created_by=self.request.user)
        log_action(user=self.request.user, action_code="risk.information_class.create", level="L2",
                   entity=instance, payload={"id": str(instance.id)})

    def perform_update(self, serializer):
        from core.scoping import require_org_scope_for_org_wide

        require_org_scope_for_org_wide(self.request.user, serializer.instance.plant)
        require_org_scope_for_org_wide(
            self.request.user, serializer.validated_data.get("plant", serializer.instance.plant),
        )
        instance = serializer.save()
        log_action(user=self.request.user, action_code="risk.information_class.update", level="L2",
                   entity=instance, payload={"id": str(instance.id)})

    def perform_destroy(self, instance):
        from core.scoping import require_org_scope_for_org_wide

        require_org_scope_for_org_wide(self.request.user, instance.plant)
        super().perform_destroy(instance)


class RiskGovernancePolicyViewSet(PlantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Policy di governo del rischio (organizzazione + eccezioni per sito)."""

    queryset = RiskGovernancePolicy.objects.select_related("plant", "approved_by")
    serializer_class = RiskGovernancePolicySerializer
    permission_classes = [RiskGovernancePermission]
    plant_field = "plant"
    allow_null_plant = True

    @action(detail=False, methods=["get"])
    def resolved(self, request):
        """Policy effettiva per `?plant=<id>` (assente = organizzazione/gruppo)."""
        from core.scoping import require_plant_access

        from core.scoping import user_has_org_scope

        from .services import TREATMENT_RULES, resolve_policy

        plant = _plant_from_param(request, request.query_params.get("plant"))
        if plant is not None:
            require_plant_access(request.user, plant)
        # `user_org_scope`: la UI mostra le modifiche di governo e il registro
        # di gruppo solo a chi può farle (il backend le verifica comunque).
        # `treatment_months`: scadenze delle misure per classe, fisse nella procedura (§9.2).
        return Response({
            **resolve_policy(plant),
            "treatment_months": {cls: rule["months"] for cls, rule in TREATMENT_RULES.items()},
            "user_org_scope": user_has_org_scope(request.user),
        })

    @action(detail=False, methods=["get"])
    def presets(self, request):
        from .services import PRESETS, preset_defaults

        return Response({name: preset_defaults(name) for name in PRESETS})

    @action(detail=False, methods=["post"], url_path="save")
    def save_policy(self, request):
        """Crea/aggiorna la policy del perimetro indicato da `plant` (null = organizzazione)."""
        from .services import save_governance_policy

        data = dict(request.data)
        plant = _plant_from_param(request, data.pop("plant", None))
        policy = _call_service(save_governance_policy, request.user, plant, data)
        return Response(self.get_serializer(policy).data)


class RiskAssessmentCycleViewSet(PlantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Cicli di valutazione dei registri (sito o gruppo)."""

    queryset = RiskAssessmentCycle.objects.select_related("plant", "approved_by_body")
    serializer_class = RiskAssessmentCycleSerializer
    permission_classes = [RiskPermission]
    plant_field = "plant"
    allow_null_plant = True

    def get_queryset(self):
        from django.db.models import Count, Q

        qs = super().get_queryset().annotate(
            risks_count=Count("risks", filter=Q(risks__deleted_at__isnull=True)),
        ).order_by("-started_at")
        plant = self.request.query_params.get("plant")
        if plant == "null":
            qs = qs.filter(plant__isnull=True)
        elif plant:
            qs = qs.filter(plant_id=plant)
        return qs

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Avvia una valutazione. Body: {plant: id|null, kind, trigger_reason}."""
        from .services import start_cycle

        plant = _plant_from_param(request, request.data.get("plant"))
        cycle = _call_service(
            start_cycle, request.user, plant,
            request.data.get("kind", ""), request.data.get("trigger_reason", ""),
        )
        return Response(self.get_serializer(cycle).data, status=201)

    def _cycle_action(self, fn, **kwargs):
        cycle = _call_service(fn, self.request.user, self.get_object(), **kwargs)
        return Response(self.get_serializer(self.get_queryset().get(pk=cycle.pk)).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._cycle_action(services.submit_cycle)

    @action(detail=True, methods=["post"], url_path="return")
    def return_to_draft(self, request, pk=None):
        return self._cycle_action(services.return_cycle, reason=request.data.get("reason", ""))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Body: {body: id organo, review?: id riesame, local_adoption_ref?}."""
        from apps.governance.models import SecurityCommittee
        from apps.management_review.models import ManagementReview

        body = SecurityCommittee.objects.filter(pk=request.data.get("body")).first()
        review = (ManagementReview.objects.filter(pk=request.data.get("review")).first()
                  if request.data.get("review") else None)
        return self._cycle_action(
            services.approve_cycle, body=body, review=review,
            local_adoption_ref=request.data.get("local_adoption_ref", ""),
        )

    @action(detail=True, methods=["get"], url_path="export", throttle_classes=[ExportRateThrottle])
    def export(self, request, pk=None):
        """Excel della fotografia congelata di una valutazione approvata."""
        from django.http import HttpResponse

        cycle = self.get_object()
        content = _call_service(services.generate_cycle_excel, cycle)
        log_action(user=request.user, action_code="risk.cycle.export", level="L2", entity=cycle,
                   payload={"plant_id": str(cycle.plant_id) if cycle.plant_id else None})
        label = cycle.plant.code if cycle.plant else "gruppo"
        date = cycle.approved_at.date().isoformat() if cycle.approved_at else "bozza"
        response = HttpResponse(
            content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="valutazione_rischi_{label}_{date}.xlsx"'
        return response

    @action(detail=True, methods=["get"], url_path="submission-check")
    def submission_check(self, request, pk=None):
        return Response({"errors": services.cycle_submission_errors(self.get_object())})
