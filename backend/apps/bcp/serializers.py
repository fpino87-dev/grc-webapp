from rest_framework import serializers
from .models import BcpPlan, BcpTest
from . import services


class BcpTestSerializer(serializers.ModelSerializer):
    objectives_met_pct = serializers.FloatField(read_only=True)
    plan_title = serializers.CharField(source="plan.title", read_only=True)
    plant = serializers.UUIDField(source="plan.plant_id", read_only=True)
    evidences_count = serializers.SerializerMethodField()

    class Meta:
        model = BcpTest
        fields = "__all__"
        # Il test si registra solo con record_test (data, esecutore, scadenza
        # del piano, PDCA su esito fallito/parziale): nessun campo scrivibile
        # direttamente.
        read_only_fields = [
            f.name for f in BcpTest._meta.fields
        ] + ["evidences"]

    def get_evidences_count(self, obj) -> int:
        return len(obj.evidences.all())


class BcpPlanSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True, default=None)
    document_code = serializers.CharField(source="document.document_code", read_only=True, default=None)
    document_status = serializers.CharField(source="document.status", read_only=True, default=None)
    process_names = serializers.SerializerMethodField()
    test_state = serializers.SerializerMethodField()
    last_test_result = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = BcpPlan
        exclude = ["content"]
        # L'approvazione passa SOLO dall'azione `approve` (verifica del ruolo
        # sul sito): senza questo lock un ruolo con permesso di scrittura
        # potrebbe auto-approvare con una PATCH. Date dei test calcolate da
        # record_test; processi coperti impostati da services.set_plan_processes.
        read_only_fields = [
            "id",
            "status",
            "approved_by",
            "approved_at",
            "last_test_date",
            "next_test_date",
            "critical_processes",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate(self, attrs):
        from django.core.exceptions import ValidationError as DjangoValidationError

        plant = attrs.get("plant") or (self.instance.plant if self.instance else None)
        if self.instance and "plant" in attrs and attrs["plant"] != self.instance.plant:
            raise serializers.ValidationError({"plant": "Il sito di un piano non si cambia."})
        if "document" in attrs and plant is not None:
            try:
                services.validate_plan_document(plant.pk, attrs["document"])
            except DjangoValidationError as e:
                raise serializers.ValidationError({"document": e.messages}) from e
        return attrs

    def _processes(self, obj):
        procs = {p.pk: p for p in obj.critical_processes.all()}
        if obj.critical_process_id and obj.critical_process:
            procs.setdefault(obj.critical_process_id, obj.critical_process)
        return sorted(procs.values(), key=lambda p: p.name)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["critical_processes"] = [str(p.pk) for p in self._processes(obj)]
        return data

    def get_process_names(self, obj) -> list[str]:
        return [p.name for p in self._processes(obj)]

    def _last_test(self, obj):
        tests = [t for t in obj.tests.all() if t.deleted_at is None]
        return max(tests, key=lambda t: (t.test_date, t.created_at)) if tests else None

    def get_test_state(self, obj) -> str:
        return services.plan_test_state(
            obj.last_test_date, obj.next_test_date, services._plant_today(obj.plant),
        )

    def get_last_test_result(self, obj):
        last = self._last_test(obj)
        return last.result if last else None

    def get_can_approve(self, obj) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        cache = self.context.setdefault("_approvable", {})
        if "ids" not in cache:
            cache["ids"] = services.approvable_plant_ids(request.user)
        return obj.status == "bozza" and services.can_approve_plan(request.user, obj, cache["ids"])
