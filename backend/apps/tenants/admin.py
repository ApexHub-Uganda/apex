from django.contrib import admin

from apps.tenants.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status", "is_verified", "is_suspended", "country", "created_at"]
    list_filter = ["status", "is_verified", "is_suspended", "country"]
    search_fields = ["name", "code", "email"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]