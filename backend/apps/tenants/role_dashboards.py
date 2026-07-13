"""Role-specific dashboard metadata for school portal users."""
from __future__ import annotations

from typing import Any

from apps.core.constants import UserRole, normalize_role
from apps.subscriptions.module_registry import SCHOOL_MODULES, get_module_for_feature


def feature_key_for_path(path: str) -> str | None:
    for module in SCHOOL_MODULES:
        if module.get("path") == path:
            keys = module.get("feature_keys") or []
            return keys[0] if keys else None
        for child in module.get("children", []):
            if child.get("path") == path:
                return child.get("feature_key")
    return None


def _readable_hub_feature_key(
    path: str,
    feature_permissions: dict[str, dict[str, bool]] | None,
) -> str | None:
    """First readable child feature for a module hub path (granular roles)."""
    if not feature_permissions:
        return None
    for module in SCHOOL_MODULES:
        if module.get("path") != path:
            continue
        for child in module.get("children", []):
            feature_key = child.get("feature_key")
            if feature_permissions.get(feature_key, {}).get("can_read"):
                return feature_key
    return None

ROLE_PROFILES: dict[str, dict[str, Any]] = {
    UserRole.SCHOOL_ADMIN: {
        "title": "School Admin Dashboard",
        "subtitle": "Full oversight of school operations, plans, and settings.",
        "icon": "FiShield",
        "accent": "primary",
        "quick_actions": [
            {"label": "Manage Staff", "path": "/school-admin/staff", "module_key": "core_management"},
            {"label": "School Settings", "path": "/school-admin/settings", "module_key": "core_management"},
            {"label": "Plans & Billing", "path": "/school-admin/settings/plans", "module_key": "core_management"},
        ],
        "widget_modules": None,
    },
    UserRole.HOSTEL_MANAGER: {
        "title": "Hostel Manager Dashboard",
        "subtitle": "Rooms, allocations, and boarding operations.",
        "icon": "FiHome",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Hostels", "path": "/school-admin/hostel", "module_key": "hostel"},
            {"label": "Room Allocations", "path": "/school-admin/hostel/allocations", "module_key": "hostel"},
        ],
        "widget_modules": ["hostel", "analytics"],
    },
    UserRole.TRANSPORT_MANAGER: {
        "title": "Transport Manager Dashboard",
        "subtitle": "Fleet, routes, and student transport assignments.",
        "icon": "FiTruck",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Vehicles", "path": "/school-admin/transport", "module_key": "transport"},
            {"label": "Routes", "path": "/school-admin/transport/routes", "module_key": "transport"},
        ],
        "widget_modules": ["transport", "analytics"],
    },
    UserRole.HR_MANAGER: {
        "title": "HR Manager Dashboard",
        "subtitle": "Leave, performance reviews, and staff lifecycle.",
        "icon": "FiUsers",
        "accent": "primary",
        "quick_actions": [
            {"label": "Manage Staffs", "path": "/school-admin/hr/staffs", "module_key": "human_resource"},
            {"label": "Leave Requests", "path": "/school-admin/hr/leave", "module_key": "human_resource"},
            {"label": "Performance Reviews", "path": "/school-admin/hr/reviews", "module_key": "human_resource"},
        ],
        "widget_modules": ["human_resource", "analytics"],
    },
    UserRole.INVENTORY_MANAGER: {
        "title": "Inventory Dashboard",
        "subtitle": "Stock, suppliers, and purchase orders.",
        "icon": "FiPackage",
        "accent": "warning",
        "quick_actions": [
            {"label": "Inventory Items", "path": "/school-admin/inventory", "module_key": "inventory"},
            {"label": "Purchase Orders", "path": "/school-admin/inventory/orders", "module_key": "inventory"},
        ],
        "widget_modules": ["inventory", "analytics"],
    },
    UserRole.LIBRARIAN: {
        "title": "Library Dashboard",
        "subtitle": "Catalog, borrowing, and returns.",
        "icon": "FiBookOpen",
        "accent": "accent",
        "quick_actions": [
            {"label": "Library Catalog", "path": "/school-admin/library", "module_key": "library"},
            {"label": "Borrowing", "path": "/school-admin/library/borrowing", "module_key": "library"},
        ],
        "widget_modules": ["library", "analytics"],
    },
    UserRole.BURSAR: {
        "title": "Bursar Dashboard",
        "subtitle": "Fees, billing, payments, and financial reports.",
        "icon": "FiDollarSign",
        "accent": "success",
        "quick_actions": [
            {"label": "Bursar Workspace", "path": "/school-admin/finance/bursar", "feature_key": "bursar_workspace"},
            {"label": "Approvals", "path": "/school-admin/finance/approval", "feature_key": "transaction_approval"},
            {"label": "Financial Reports", "path": "/school-admin/finance/reports", "feature_key": "financial_reports"},
        ],
        "widget_modules": ["finance", "analytics"],
    },
    UserRole.ASSISTANT_BURSAR: {
        "title": "Assistant Bursar Dashboard",
        "subtitle": "Daily collections, invoicing, and student accounts.",
        "icon": "FiCreditCard",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Assistant Workspace", "path": "/school-admin/finance/assistant", "feature_key": "assistant_bursar_workspace"},
            {"label": "Record Payment", "path": "/school-admin/finance/payments", "feature_key": "payment_recording"},
            {"label": "Student Billing", "path": "/school-admin/finance", "feature_key": "student_billing"},
        ],
        "widget_modules": ["finance", "analytics"],
    },
    UserRole.DIRECTOR_OF_STUDIES: {
        "title": "Director of Studies Dashboard",
        "subtitle": "Academics, examinations, and attendance oversight.",
        "icon": "FiBook",
        "accent": "primary",
        "quick_actions": [
            {"label": "DoS Workspace", "path": "/school-admin/academics/dos", "feature_key": "dos_workspace"},
            {"label": "Marks Approval", "path": "/school-admin/examinations/approval", "feature_key": "marks_approval"},
            {"label": "Teacher Assignments", "path": "/school-admin/academics/teacher-assignments", "feature_key": "teacher_assignments"},
        ],
        "widget_modules": ["academics", "examinations", "attendance", "analytics"],
    },
    UserRole.HEAD_TEACHER: {
        "title": "Head Teacher Dashboard",
        "subtitle": "School-wide academic leadership and communication.",
        "icon": "FiAward",
        "accent": "primary",
        "quick_actions": [
            {"label": "Academics", "path": "/school-admin/academics", "module_key": "academics"},
            {"label": "Staff", "path": "/school-admin/staff", "module_key": "core_management"},
            {"label": "Announcements", "path": "/school-admin/communication", "module_key": "communication"},
        ],
        "widget_modules": ["academics", "attendance", "examinations", "communication", "analytics"],
    },
    UserRole.DEPUTY_HEAD_TEACHER: {
        "title": "Deputy Head Teacher Dashboard",
        "subtitle": "Day-to-day academic and attendance coordination.",
        "icon": "FiUserCheck",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Classes", "path": "/school-admin/classes", "module_key": "academics"},
            {"label": "Attendance", "path": "/school-admin/attendance", "module_key": "attendance"},
        ],
        "widget_modules": ["academics", "attendance", "analytics"],
    },
    UserRole.TEACHER: {
        "title": "Teacher Dashboard",
        "subtitle": "Classes, attendance, and academic tasks.",
        "icon": "FiBookOpen",
        "accent": "primary",
        "quick_actions": [
            {"label": "Teacher Workspace", "path": "/school-admin/academics/teacher", "feature_key": "teacher_workspace"},
            {"label": "Student Attendance", "path": "/school-admin/attendance", "feature_key": "student_attendance"},
            {"label": "Marks Entry", "path": "/school-admin/examinations/marks", "feature_key": "marks_entry"},
            {"label": "Lesson Attendance", "path": "/school-admin/attendance/lessons", "feature_key": "lesson_attendance"},
        ],
        "widget_modules": ["academics", "attendance", "examinations", "analytics"],
    },
    UserRole.CLASS_TEACHER: {
        "title": "Class Teacher Dashboard",
        "subtitle": "Class welfare, notices, discipline, and student support.",
        "icon": "FiUsers",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Class Teacher Tools", "path": "/school-admin/academics/class-teacher", "feature_key": "class_teacher_tools"},
            {"label": "Student Attendance", "path": "/school-admin/attendance", "feature_key": "student_attendance"},
            {"label": "Class Notices", "path": "/school-admin/academics/class-notices", "feature_key": "class_notices"},
            {"label": "Discipline Remarks", "path": "/school-admin/academics/discipline", "feature_key": "discipline_remarks"},
            {"label": "Marks Entry", "path": "/school-admin/examinations/marks", "feature_key": "marks_entry"},
        ],
        "widget_modules": ["academics", "attendance", "examinations", "analytics"],
    },
    UserRole.HEAD_OF_DEPARTMENT: {
        "title": "Head of Department Dashboard",
        "subtitle": "Department academics and examination coordination.",
        "icon": "FiLayers",
        "accent": "accent",
        "quick_actions": [
            {"label": "HoD Workspace", "path": "/school-admin/academics/hod", "feature_key": "hod_workspace"},
            {"label": "Marks Approval", "path": "/school-admin/examinations/approval", "feature_key": "marks_approval"},
            {"label": "Subjects", "path": "/school-admin/academics/subjects", "feature_key": "subjects"},
        ],
        "widget_modules": ["academics", "examinations", "analytics"],
    },
    UserRole.PARENT: {
        "title": "Parent Portal",
        "subtitle": "Fees, announcements, and your child's school updates.",
        "icon": "FiHeart",
        "accent": "secondary",
        "quick_actions": [
            {"label": "Announcements", "path": "/school-admin/communication", "module_key": "communication"},
            {"label": "Fee Status", "path": "/school-admin/finance", "module_key": "finance"},
        ],
        "widget_modules": ["communication", "finance", "events", "analytics"],
    },
}


def get_role_profile(user) -> dict[str, Any]:
    role = normalize_role(getattr(user, "role", UserRole.TEACHER))
    profile = ROLE_PROFILES.get(role, ROLE_PROFILES[UserRole.TEACHER]).copy()
    profile["role"] = role
    profile["role_label"] = dict(UserRole.CHOICES).get(role, role.replace("_", " ").title())
    return profile


def filter_quick_actions(
    profile: dict[str, Any],
    module_permissions: dict[str, dict[str, bool]],
    feature_permissions: dict[str, dict[str, bool]] | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for action in profile.get("quick_actions", []):
        module_key = action.get("module_key")
        feature_key = action.get("feature_key") or feature_key_for_path(action.get("path", ""))

        if feature_permissions is not None:
            resolved_key = feature_key
            feat_perms = feature_permissions.get(resolved_key or "", {})
            if not feat_perms.get("can_read"):
                resolved_key = _readable_hub_feature_key(action.get("path", ""), feature_permissions)
                feat_perms = feature_permissions.get(resolved_key or "", {})
            if not resolved_key or not feat_perms.get("can_read"):
                continue
            actions.append({
                **action,
                "feature_key": resolved_key,
                "can_write": feat_perms.get("can_write", False),
            })
            continue

        if not module_key:
            actions.append(action)
            continue

        perms = module_permissions.get(module_key, {})
        if perms.get("can_read"):
            actions.append({**action, "can_write": perms.get("can_write", False)})
    return actions


def filter_dashboard_widgets(
    plan_widgets: list[dict[str, Any]],
    module_permissions: dict[str, dict[str, bool]],
    profile: dict[str, Any],
    feature_permissions: dict[str, dict[str, bool]] | None = None,
) -> list[dict[str, Any]]:
    allowed_modules = profile.get("widget_modules")
    if allowed_modules is None:
        return plan_widgets

    allowed_set = set(allowed_modules)
    filtered: list[dict[str, Any]] = []
    for widget in plan_widgets:
        feature_key = widget.get("feature_key", "")
        if feature_permissions is not None and feature_key:
            if not feature_permissions.get(feature_key, {}).get("can_read"):
                continue
        module = get_module_for_feature(feature_key)
        module_key = module["key"] if module else None
        if module_key and module_key in allowed_set:
            perms = module_permissions.get(module_key, {})
            if perms.get("can_read"):
                feat_write = feature_permissions.get(feature_key, {}).get("can_write", False) if feature_permissions else perms.get("can_write", False)
                filtered.append({**widget, "can_write": feat_write})
    return filtered