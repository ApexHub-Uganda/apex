from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import LoginHistory, User, UserDevice, UserProfilePicture, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role", "tenant", "is_active", "is_email_verified"]
    list_filter = ["role", "is_active", "is_email_verified", "tenant"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    readonly_fields = ["id", "last_login", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Access", {"fields": ("role", "tenant", "is_active", "is_staff", "is_superuser")}),
        ("Verification", {"fields": ("is_email_verified", "email_verified_at")}),
        ("2FA", {"fields": ("is_2fa_enabled", "totp_secret")}),
        ("Timestamps", {"fields": ("last_login", "last_login_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "first_name", "last_name", "role", "tenant"),
        }),
    )


@admin.register(UserProfilePicture)
class UserProfilePictureAdmin(admin.ModelAdmin):
    list_display = ["user", "original_filename", "file_size", "uploaded_at"]
    search_fields = ["user__email", "original_filename"]
    readonly_fields = ["uploaded_at", "updated_at"]


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "device_name", "ip_address", "is_active", "last_activity"]
    list_filter = ["is_active", "device_type"]


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "device_name", "platform", "is_trusted", "last_seen"]


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ["email", "success", "ip_address", "created_at"]
    list_filter = ["success"]