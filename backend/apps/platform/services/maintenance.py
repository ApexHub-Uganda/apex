"""Maintenance mode helpers — runtime flag, DB sync, and request auth."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.core.constants import UserRole
from apps.platform.models import GlobalSetting

User = get_user_model()

MAINTENANCE_MESSAGE = "Apex Hub is currently under maintenance. Please try again later."

BYPASS_PATH_PREFIXES = (
    "/api/v1/auth/login/",
    "/api/v1/auth/refresh/",
    "/api/v1/platform/health/",
    "/admin/",
)


def is_maintenance_mode() -> bool:
    if not getattr(settings, "_MAINTENANCE_MODE_LOADED", False):
        load_maintenance_mode_from_db()
    return bool(getattr(settings, "MAINTENANCE_MODE", False))


def set_maintenance_mode(enabled: bool) -> None:
    settings.MAINTENANCE_MODE = bool(enabled)
    settings._MAINTENANCE_MODE_LOADED = True
    GlobalSetting.objects.update_or_create(
        key="maintenance_mode",
        defaults={"value": {"enabled": bool(enabled)}},
    )


def load_maintenance_mode_from_db() -> bool:
    """Hydrate in-memory flag from persisted platform settings."""
    try:
        setting = GlobalSetting.objects.filter(key="maintenance_mode").first()
        if setting is not None:
            settings.MAINTENANCE_MODE = bool(setting.value.get("enabled", False))
    except Exception:
        settings.MAINTENANCE_MODE = bool(getattr(settings, "MAINTENANCE_MODE", False))
    settings._MAINTENANCE_MODE_LOADED = True
    return bool(settings.MAINTENANCE_MODE)


def authenticate_request_user(request):
    """Resolve the API user from JWT (DRF auth runs after Django middleware)."""
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication

        result = JWTAuthentication().authenticate(request)
        if result:
            return result[0]
    except Exception:
        pass

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def is_super_admin(user) -> bool:
    return bool(user and getattr(user, "role", None) == UserRole.SUPER_ADMIN)


def should_bypass_maintenance(request) -> bool:
    if any(request.path.startswith(prefix) for prefix in BYPASS_PATH_PREFIXES):
        return True
    user = authenticate_request_user(request)
    return is_super_admin(user)