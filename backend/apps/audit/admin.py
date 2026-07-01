from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "resource_type", "user", "tenant", "status_code", "created_at"]
    list_filter = ["action", "resource_type"]
    search_fields = ["description", "resource_id"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]