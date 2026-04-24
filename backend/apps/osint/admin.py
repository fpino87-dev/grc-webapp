from django.contrib import admin

from .models import (
    OsintAlert,
    OsintEntity,
    OsintScan,
    OsintSettings,
    OsintSubdomain,
)


@admin.register(OsintEntity)
class OsintEntityAdmin(admin.ModelAdmin):
    list_display = ("display_name", "domain", "entity_type", "source_module", "is_nis2_critical", "is_active", "scan_frequency")
    list_filter = ("entity_type", "source_module", "is_active", "is_nis2_critical")
    search_fields = ("display_name", "domain")
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(OsintScan)
class OsintScanAdmin(admin.ModelAdmin):
    list_display = ("entity", "scan_date", "status", "score_total")
    list_filter = ("status",)
    search_fields = ("entity__domain", "entity__display_name")
    readonly_fields = ("scan_date", "created_at", "updated_at", "deleted_at")


@admin.register(OsintSubdomain)
class OsintSubdomainAdmin(admin.ModelAdmin):
    list_display = ("subdomain", "entity", "status", "first_seen", "last_seen")
    list_filter = ("status",)
    search_fields = ("subdomain",)


@admin.register(OsintAlert)
class OsintAlertAdmin(admin.ModelAdmin):
    list_display = ("entity", "alert_type", "severity", "status", "created_at")
    list_filter = ("severity", "status", "alert_type")
    search_fields = ("entity__domain", "description")


@admin.register(OsintSettings)
class OsintSettingsAdmin(admin.ModelAdmin):
    list_display = ("score_threshold_critical", "score_threshold_warning", "anonymization_enabled")

    def has_add_permission(self, request):
        # Singleton — blocca creazione di più righe dall'admin
        if OsintSettings.objects.exists():
            return False
        return super().has_add_permission(request)
