from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as django_validate_password
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.audit import log_action
from .models import UserPlantAccess, GrcRole
from .permissions import IsGrcSuperAdmin
from .services import anonymize_user


def _validate_password_policy(value):
    """Applica i validator password di progetto (12+ char, CommonPassword,
    NumericPassword, ...) ai flussi admin di creazione/reset, che prima si
    fermavano a min_length=8 bypassando la policy."""
    django_validate_password(value)
    return value

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    grc_role = serializers.SerializerMethodField()
    plant_access = serializers.SerializerMethodField()
    # Gestione utenti: accessi descritti (ruolo + perimetro), responsabilità
    # attive, avvisi di coerenza, MFA e ultimo accesso (prefetch nel ViewSet).
    accesses = serializers.SerializerMethodField()
    responsibilities = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()
    mfa_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "is_active", "is_staff", "is_superuser", "date_joined", "last_login",
                  "grc_role", "plant_access", "accesses", "responsibilities", "warnings", "mfa_enabled"]
        read_only_fields = ["id", "date_joined", "last_login", "grc_role", "plant_access",
                            "accesses", "responsibilities", "warnings", "mfa_enabled"]

    def _bu_plants(self):
        from .services import bu_plants_map
        if "bu_plants" not in self.context:
            self.context["bu_plants"] = bu_plants_map()
        return self.context["bu_plants"]

    def _responsibilities(self, obj):
        prefetched = getattr(obj, "active_responsibilities", None)
        if prefetched is not None:
            return prefetched
        return [r for r in obj.role_assignments.all() if r.is_active]

    def get_accesses(self, obj):
        from .models import GrcRole
        rows = []
        for a in obj.plant_access.all():
            try:
                label = str(GrcRole(a.role).label)
            except ValueError:
                label = a.role
            rows.append({
                "id": str(a.id), "role": a.role, "role_label": label, "scope_type": a.scope_type,
                "scope_bu_code": a.scope_bu.code if a.scope_bu_id else None,
                "scope_plant_codes": sorted(p.code for p in a.scope_plants.all()),
            })
        return rows

    def _scope_codes(self):
        """{id: codice} di siti e BU, caricato una volta per l'elenco."""
        from apps.plants.models import BusinessUnit, Plant
        if "scope_codes" not in self.context:
            codes = dict(Plant.objects.values_list("pk", "code"))
            codes.update(BusinessUnit.objects.values_list("pk", "code"))
            self.context["scope_codes"] = codes
        return self.context["scope_codes"]

    def get_responsibilities(self, obj):
        rows = []
        for r in self._responsibilities(obj):
            code = self._scope_codes().get(r.scope_id) if r.scope_id else None
            rows.append({"id": str(r.id), "role": r.role, "scope_type": r.scope_type,
                         "scope_id": str(r.scope_id) if r.scope_id else None, "scope_code": code,
                         "valid_until": r.valid_until.isoformat() if r.valid_until else None})
        return rows

    def get_warnings(self, obj):
        from .services import responsibility_access_gaps
        return responsibility_access_gaps(
            obj, list(obj.plant_access.all()), self._responsibilities(obj), self._bu_plants(),
        )

    def get_mfa_enabled(self, obj):
        annotated = getattr(obj, "mfa_confirmed", None)
        if annotated is not None:
            return bool(annotated)
        from django_otp import devices_for_user
        return bool(list(devices_for_user(obj)))

    def get_grc_role(self, obj):
        if obj.is_superuser:
            return "super_admin"
        # Usa il related manager (prefetchato dal ViewSet sul listing → niente N+1).
        accesses = list(obj.plant_access.all())
        return accesses[0].role if accesses else None

    def get_plant_access(self, obj):
        return [
            {"id": str(a.id), "role": a.role, "scope_type": a.scope_type}
            for a in obj.plant_access.all()
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[_validate_password_policy])
    # esponiamo solo un sottoinsieme dei ruoli GRC per la UI
    EXPOSED_ROLES = [
        (GrcRole.SUPER_ADMIN, "Super Admin"),
        (GrcRole.PLANT_MANAGER, "Plant Admin"),
        (GrcRole.CONTROL_OWNER, "User"),
    ]
    grc_role = serializers.ChoiceField(choices=[r[0] for r in EXPOSED_ROLES], required=False, write_only=True)
    # Accessi creati insieme all'utente: [{role, scope_type, scope_plants?, scope_bu?}]
    accesses = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "is_staff", "grc_role", "accesses"]

    def create(self, validated_data):
        from .services import create_grc_user

        grc_role = validated_data.pop("grc_role", None)
        accesses = validated_data.pop("accesses", None) or []
        password = validated_data.pop("password")
        if grc_role and not accesses:
            accesses = [{"role": grc_role, "scope_type": "org"}]
        return create_grc_user(
            actor=self.context["request"].user, data=validated_data, password=password, accesses=accesses,
        )


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(validators=[_validate_password_policy])


class AssignRoleSerializer(serializers.Serializer):
    # stessi ruoli esposti in creazione
    EXPOSED_ROLES = UserCreateSerializer.EXPOSED_ROLES
    role = serializers.ChoiceField(choices=[r[0] for r in EXPOSED_ROLES])
    # Solo 'org': questo endpoint imposta il ruolo "primario" org-wide e non
    # accetta i siti, quindi un perimetro per-sito qui creerebbe un accesso
    # VUOTO. Gli accessi per-sito si gestiscono via UserPlantAccessViewSet
    # (/auth/plant-access/) col selettore siti.
    scope_type = serializers.ChoiceField(choices=["org"], default="org")


class UserViewSet(viewsets.ModelViewSet):
    # prefetch_related("plant_access"): il UserSerializer legge ruolo + accessi
    # per ogni utente → senza prefetch sarebbe 2N+ query sul listing.
    queryset = User.objects.all().order_by("username").prefetch_related("plant_access")
    filterset_fields = ["is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]

    def get_queryset(self):
        """Elenco: di default solo gli attivi (gli altri moduli scelgono owner
        e destinatari fra questi); ?status=inactive|all per la gestione utenti.
        Le azioni di dettaglio vedono tutti, così un disattivato si riattiva."""
        from django.db.models import Exists, OuterRef, Prefetch, Q
        from django.utils import timezone
        from django_otp.plugins.otp_totp.models import TOTPDevice

        from apps.governance.models import RoleAssignment

        today = timezone.localdate()
        qs = super().get_queryset().prefetch_related(
            "plant_access__scope_plants", "plant_access__scope_bu",
            Prefetch(
                "role_assignments",
                queryset=RoleAssignment.objects.filter(valid_from__lte=today).filter(
                    Q(valid_until__isnull=True) | Q(valid_until__gte=today)
                ),
                to_attr="active_responsibilities",
            ),
        ).annotate(mfa_confirmed=Exists(TOTPDevice.objects.filter(user=OuterRef("pk"), confirmed=True)))
        if self.action == "list":
            status_param = self.request.query_params.get("status", "active")
            if status_param == "active" and "is_active" not in self.request.query_params:
                qs = qs.filter(is_active=True)
            elif status_param == "inactive":
                qs = qs.filter(is_active=False)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["me", "list_roles", "role_matrix"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsGrcSuperAdmin()]

    def destroy(self, request, *args, **kwargs):
        # "Cancella utente": anonimizza (GDPR Art. 17) invece di soft-delete.
        # Rispetto a deactivate_grc_user questo libera username/email (li
        # riassegna a deleted_<id>@anonymized.invalid), così l'utente può
        # essere ricreato con lo stesso username. I record collegati restano
        # ma perdono il riferimento all'identità reale.
        user = self.get_object()
        # Stesse guardie di deactivate_grc_user: no auto-cancellazione, un
        # non-superuser non può rimuovere un superuser.
        if user.pk == request.user.pk:
            return Response(
                {"detail": "Non puoi cancellare il tuo account da qui."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {"detail": "Operazione non consentita su un account superuser."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        anonymize_user(user, request.user, reason="Cancellazione da gestione utenti")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save()
        # Reset password da parte di un admin: azione privilegiata → audit
        # (ISO 27001 A.9.4.3). Il signal revoca anche i TrustedDevice.
        log_action(
            user=request.user,
            action_code="auth.user.password_reset",
            level="L2",
            entity=user,
            payload={"user_id": user.pk},
        )
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def assign_role(self, request, pk=None):
        from django.utils import timezone
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        scope_type = serializer.validated_data["scope_type"]
        # Sostituisce l'accesso org esistente: soft delete (regola #5), non hard
        # delete come prima.
        UserPlantAccess.objects.filter(
            user=user, scope_type="org", deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())
        access = UserPlantAccess.objects.create(
            user=user, role=role, scope_type=scope_type, created_by=request.user,
        )
        log_action(
            user=request.user,
            action_code="auth.access.granted",
            level="L2",
            entity=access,
            payload={"user_id": user.pk, "role": role, "scope_type": scope_type},
        )
        return Response({"ok": True, "role": role})

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        log_action(
            user=request.user,
            action_code="auth.user.activated" if user.is_active else "auth.user.deactivated",
            level="L2",
            entity=user,
            payload={"user_id": user.pk, "is_active": user.is_active},
        )
        return Response({"is_active": user.is_active})

    @action(detail=False, methods=["get"], url_path="role-matrix", permission_classes=[IsAuthenticated])
    def role_matrix(self, request):
        """Cosa può fare ogni ruolo, per area (letto dalle permission class)."""
        from .services import role_permission_matrix
        return Response(role_permission_matrix())

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def list_roles(self, request):
        # restituiamo solo il sottoinsieme di ruoli GRC usati per la gestione utenti
        return Response(
            [{"value": value, "label": label} for value, label in UserCreateSerializer.EXPOSED_ROLES]
        )
