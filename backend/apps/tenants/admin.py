from django.contrib import admin

from apps.tenants.models import SchoolRoleFeaturePermission, SchoolRoleModulePermission, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status", "is_verified", "is_suspended", "country", "created_at"]
    list_filter = ["status", "is_verified", "is_suspended", "country"]
    search_fields = ["name", "code", "email"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]


@admin.register(SchoolRoleFeaturePermission)
class SchoolRoleFeaturePermissionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "role", "feature_key", "can_read", "can_write", "updated_at"]
    list_filter = ["role", "can_read", "can_write"]
    search_fields = ["tenant__name", "tenant__code", "role", "feature_key"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(SchoolRoleModulePermission)
class SchoolRoleModulePermissionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "role", "module_key", "can_read", "can_write", "updated_at"]
    list_filter = ["role", "module_key", "can_read", "can_write"]
    search_fields = ["tenant__name", "tenant__code", "role", "module_key"]
    readonly_fields = ["id", "created_at", "updated_at"]