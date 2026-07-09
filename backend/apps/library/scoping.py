"""Library data access — gated by Permission Settings feature grants."""
from __future__ import annotations

from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin

LIBRARY_SCHOOL_WIDE_FEATURES = frozenset({
    "librarian_workspace",
    "library_management",
    "book_categories",
    "borrowing",
    "returns",
    "reservations",
    "library_fines",
    "book_suppliers",
    "library_reports",
})


def user_has_school_wide_library_access(user, tenant=None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    perms = get_user_feature_permissions(tenant, user)
    return any(perms.get(key, {}).get("can_read") for key in LIBRARY_SCHOOL_WIDE_FEATURES)


def filter_library_queryset_for_user(queryset, user):
    """Tenant filtering is handled by TenantFilterMixin; library requires feature grants."""
    if user_has_school_wide_library_access(user, getattr(user, "tenant", None)):
        return queryset
    return queryset.none()