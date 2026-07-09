"""HR role workspace summaries."""
from __future__ import annotations

from typing import Any

from apps.core.constants import UserRole, normalize_role
from apps.hr.constants import LEAVE_PENDING
from apps.academics.models import Department
from apps.hr.constants import REVIEW_DRAFT, REVIEW_SUBMITTED
from apps.hr.models import Leave, PerformanceReview
from apps.hr.scoping import user_has_school_wide_hr_access
from apps.staff.models import Staff
from apps.tenants.role_permissions import get_user_feature_permissions


def _enabled(perms: dict, key: str) -> bool:
    return bool(perms.get(key, {}).get("can_read"))


def build_hr_workspace(*, tenant, user) -> dict[str, Any]:
    role = normalize_role(getattr(user, "role", ""))
    perms = get_user_feature_permissions(tenant, user)
    is_school_wide = user_has_school_wide_hr_access(user, tenant)

    payload: dict[str, Any] = {
        "role": role,
        "is_school_wide": is_school_wide,
        "features": {
            key: perms.get(key, {"can_read": False, "can_write": False})
            for key in (
                "hr_manager_workspace", "staff_management", "leave_requests",
                "performance_reviews", "staff_contracts", "staff_discipline",
                "staff_qualifications", "staff_documents", "work_schedules",
                "hr_reports", "hr_analytics", "staff_attendance",
            )
        },
        "counts": {},
        "queues": {},
        "quick_links": [],
    }

    if not is_school_wide:
        return payload

    if _enabled(perms, "staff_management"):
        payload["counts"]["staff_count"] = Staff.objects.filter(
            tenant=tenant, is_deleted=False, status="active",
        ).count()

    if _enabled(perms, "hr_departments"):
        payload["counts"]["departments"] = Department.objects.filter(
            tenant=tenant, is_deleted=False,
        ).count()

    if _enabled(perms, "performance_reviews"):
        payload["counts"]["pending_reviews"] = PerformanceReview.objects.filter(
            tenant=tenant, is_deleted=False, status__in=[REVIEW_DRAFT, REVIEW_SUBMITTED],
        ).count()

    if _enabled(perms, "leave_requests"):
        pending_leaves = Leave.objects.filter(
            tenant=tenant, is_deleted=False, status=LEAVE_PENDING,
        ).select_related("staff")[:20]
        pending_count = Leave.objects.filter(
            tenant=tenant, is_deleted=False, status=LEAVE_PENDING,
        ).count()
        payload["counts"]["pending_leaves"] = pending_count
        payload["counts"]["pending_leave"] = pending_count
        payload["queues"]["pending_leaves"] = [
            {
                "id": str(leave.id),
                "staff": leave.staff.full_name if leave.staff_id else "",
                "leave_type": leave.leave_type,
                "start_date": str(leave.start_date),
                "end_date": str(leave.end_date),
                "days": leave.days,
            }
            for leave in pending_leaves
        ]
        payload["queues"]["pending_leave_requests"] = payload["queues"]["pending_leaves"]

    if role == UserRole.HR_MANAGER and _enabled(perms, "hr_manager_workspace"):
        payload["quick_links"] = [
            {"label": "Staff Management", "path": "/school-admin/hr/staffs", "feature_key": "staff_management"},
            {"label": "Leave Approval", "path": "/school-admin/hr/approval", "feature_key": "leave_requests"},
            {"label": "Leave Requests", "path": "/school-admin/hr/leave", "feature_key": "leave_requests"},
            {"label": "Performance Reviews", "path": "/school-admin/hr/reviews", "feature_key": "performance_reviews"},
            {"label": "HR Analytics", "path": "/school-admin/hr/analytics", "feature_key": "hr_analytics"},
            {"label": "HR Reports", "path": "/school-admin/hr/reports", "feature_key": "hr_reports"},
        ]

    return payload