"""Hostel data access — warden-scoped for managers, school-wide for admins."""
from __future__ import annotations

from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin

HOSTEL_SCHOOL_WIDE_FEATURES = frozenset({
    "hostel_manager_workspace",
    "hostel_management",
    "rooms",
    "room_allocation",
    "hostel_maintenance",
    "hostel_visitors",
    "hostel_discipline",
    "hostel_inventory",
    "hostel_fees",
    "hostel_reports",
})


def _staff_profile_for_user(user):
    return getattr(user, "staff_profile", None)


def managed_hostel_ids_for_user(user, tenant=None) -> list | None:
    """Return hostel IDs the user manages, or None for school-wide access."""
    if not user or not getattr(user, "is_authenticated", False):
        return []
    if user_is_school_admin(user):
        return None
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return []
    perms = get_user_feature_permissions(tenant, user)
    if not any(perms.get(key, {}).get("can_read") for key in HOSTEL_SCHOOL_WIDE_FEATURES):
        return []
    staff = _staff_profile_for_user(user)
    if staff is None:
        return None
    from apps.hostel.models import Hostel

    return list(
        Hostel.objects.filter(tenant=tenant, is_deleted=False, warden=staff).values_list("id", flat=True),
    )


def user_has_hostel_access(user, tenant=None) -> bool:
    ids = managed_hostel_ids_for_user(user, tenant)
    return ids is None or bool(ids)


def filter_hostel_queryset_for_user(queryset, user, *, hostel_field: str = "id"):
    ids = managed_hostel_ids_for_user(user, getattr(user, "tenant", None))
    if ids is None:
        return queryset
    if not ids:
        return queryset.none()
    return queryset.filter(**{f"{hostel_field}__in": ids})


def filter_by_managed_hostels(queryset, user, *, hostel_path: str = "hostel_id"):
    ids = managed_hostel_ids_for_user(user, getattr(user, "tenant", None))
    if ids is None:
        return queryset
    if not ids:
        return queryset.none()
    return queryset.filter(**{f"{hostel_path}__in": ids})