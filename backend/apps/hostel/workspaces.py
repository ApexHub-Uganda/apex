"""Hostel role workspace summaries."""
from __future__ import annotations

from typing import Any

from django.db.models import Sum

from apps.core.constants import UserRole, normalize_role
from apps.hostel.constants import ALLOCATION_OCCUPYING_STATUSES, MAINTENANCE_OPEN_STATUSES
from apps.hostel.models import Allocation, Hostel, HostelFee, HostelMaintenance, Room
from apps.hostel.scoping import filter_by_managed_hostels, managed_hostel_ids_for_user, user_has_hostel_access
from apps.tenants.role_permissions import get_user_feature_permissions


def _enabled(perms: dict, key: str) -> bool:
    return bool(perms.get(key, {}).get("can_read"))


def build_hostel_workspace(*, tenant, user) -> dict[str, Any]:
    role = normalize_role(getattr(user, "role", ""))
    perms = get_user_feature_permissions(tenant, user)
    has_access = user_has_hostel_access(user, tenant)

    managed_ids = managed_hostel_ids_for_user(user, tenant)

    payload: dict[str, Any] = {
        "role": role,
        "is_school_wide": managed_ids is None and has_access,
        "managed_hostel_count": len(managed_ids or []),
        "features": {
            key: perms.get(key, {"can_read": False, "can_write": False})
            for key in (
                "hostel_manager_workspace", "hostel_management", "rooms",
                "room_allocation", "hostel_maintenance", "hostel_visitors",
                "hostel_discipline", "hostel_inventory", "hostel_fees", "hostel_reports",
            )
        },
        "counts": {},
        "queues": {},
        "quick_links": [],
    }

    if not has_access:
        return payload

    hostels = Hostel.objects.filter(tenant=tenant, is_deleted=False)
    rooms = Room.objects.filter(tenant=tenant, is_deleted=False)
    allocations = Allocation.objects.filter(tenant=tenant, is_deleted=False)
    maintenance = HostelMaintenance.objects.filter(tenant=tenant, is_deleted=False)

    hostels = filter_by_managed_hostels(hostels, user, hostel_path="id")
    hostel_ids = list(hostels.values_list("id", flat=True))
    if hostel_ids:
        rooms = rooms.filter(hostel_id__in=hostel_ids)
        allocations = allocations.filter(room__hostel_id__in=hostel_ids)
        maintenance = maintenance.filter(hostel_id__in=hostel_ids)

    if _enabled(perms, "hostel_management"):
        hostel_count = hostels.count()
        payload["counts"]["hostels"] = hostel_count
        payload["counts"]["total_hostels"] = hostel_count

    if _enabled(perms, "rooms"):
        room_count = rooms.count()
        payload["counts"]["rooms"] = room_count
        payload["counts"]["total_rooms"] = room_count
        cap = rooms.aggregate(total=Sum("capacity"))["total"] or 0
        occ = rooms.aggregate(occ=Sum("occupied"))["occ"] or 0
        vacant = max(cap - occ, 0)
        payload["counts"]["available_beds"] = vacant
        payload["counts"]["vacant_beds"] = vacant

    if _enabled(perms, "room_allocation"):
        payload["counts"]["active_allocations"] = allocations.filter(
            status__in=ALLOCATION_OCCUPYING_STATUSES,
        ).count()

    if _enabled(perms, "hostel_maintenance"):
        open_qs = maintenance.filter(status__in=MAINTENANCE_OPEN_STATUSES)
        payload["counts"]["open_maintenance"] = open_qs.count()
        payload["queues"]["maintenance"] = [
            {
                "id": str(item.id),
                "title": item.title,
                "hostel": item.hostel.name,
                "priority": item.priority,
                "status": item.status,
            }
            for item in open_qs.select_related("hostel")[:10]
        ]
        payload["queues"]["pending_allocations"] = payload["queues"]["maintenance"]

    if _enabled(perms, "hostel_fees"):
        payload["counts"]["pending_fees"] = HostelFee.objects.filter(
            tenant=tenant, is_deleted=False, status__in=["pending", "partial", "overdue"],
            hostel_id__in=hostel_ids if hostel_ids else Hostel.objects.filter(tenant=tenant).values_list("id", flat=True),
        ).count()

    if role == UserRole.HOSTEL_MANAGER and _enabled(perms, "hostel_manager_workspace"):
        payload["quick_links"] = [
            {"label": "Hostel Workspace", "path": "/school-admin/hostel/manager", "feature_key": "hostel_manager_workspace"},
            {"label": "Room Allocations", "path": "/school-admin/hostel/allocations", "feature_key": "room_allocation"},
            {"label": "Maintenance", "path": "/school-admin/hostel/maintenance", "feature_key": "hostel_maintenance"},
            {"label": "Visitor Log", "path": "/school-admin/hostel/visitors", "feature_key": "hostel_visitors"},
            {"label": "Hostel Reports", "path": "/school-admin/hostel/reports", "feature_key": "hostel_reports"},
        ]

    return payload