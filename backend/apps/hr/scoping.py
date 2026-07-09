"""HR data access — gated by Permission Settings feature grants."""
from __future__ import annotations

from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin

HR_SCHOOL_WIDE_FEATURES = frozenset({
    "hr_manager_workspace",
    "staff_management",
    "hr_departments",
    "positions",
    "leave_types",
    "leave_requests",
    "performance_reviews",
    "staff_attendance",
    "staff_contracts",
    "staff_discipline",
    "staff_qualifications",
    "staff_documents",
    "work_schedules",
    "hr_reports",
    "hr_analytics",
})


def user_has_school_wide_hr_access(user, tenant=None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    perms = get_user_feature_permissions(tenant, user)
    return any(perms.get(key, {}).get("can_read") for key in HR_SCHOOL_WIDE_FEATURES)


def filter_hr_queryset_for_user(queryset, user):
    """Tenant filtering is handled by TenantFilterMixin; HR requires feature grants."""
    if user_has_school_wide_hr_access(user, getattr(user, "tenant", None)):
        return queryset
    return queryset.none()


def user_can_manage_leave_requests(user, tenant=None) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    from apps.tenants.role_permissions import user_can_access_feature

    return user_can_access_feature(tenant, user, "leave_requests", require_write=True)


def user_can_manage_performance_reviews(user, tenant=None) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    from apps.tenants.role_permissions import user_can_access_feature

    return user_can_access_feature(tenant, user, "performance_reviews", require_write=True)