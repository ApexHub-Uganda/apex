"""Role- and plan-aware global portal search."""
from __future__ import annotations

import re
from typing import Any

from django.db.models import Q

from apps.core.constants import UserRole, normalize_role
from apps.tenants.role_dashboards import filter_quick_actions, get_role_profile
from apps.tenants.role_permissions import get_user_module_menu, get_user_module_permissions, user_is_school_admin

SUPER_ADMIN_SEARCH_ENTRIES: list[dict[str, Any]] = [
    {"title": "Dashboard", "subtitle": "Platform overview", "path": "/super-admin", "icon": "FiHome", "category": "Pages", "keywords": ["home", "overview"]},
    {"title": "Notifications Inbox", "subtitle": "Platform notifications", "path": "/super-admin/notifications", "icon": "FiInbox", "category": "Notifications", "keywords": ["alerts", "inbox"]},
    {"title": "Plan Advertisements", "subtitle": "Promote plans to schools", "path": "/super-admin/notifications/advertise", "icon": "FiTrendingUp", "category": "Notifications", "keywords": ["ads", "promotions"]},
    {"title": "Schools", "subtitle": "Manage registered schools", "path": "/super-admin/schools", "icon": "FiGrid", "category": "Management", "keywords": ["tenants", "institutions"]},
    {"title": "Plans & Subscriptions", "subtitle": "Subscription plans and features", "path": "/super-admin/plans", "icon": "FiLayers", "category": "Management", "keywords": ["pricing", "features", "tiers"]},
    {"title": "Billing & Payments", "subtitle": "Payment transactions", "path": "/super-admin/billing", "icon": "FiCreditCard", "category": "Management", "keywords": ["invoices", "revenue"]},
    {"title": "Analytics", "subtitle": "Platform analytics", "path": "/super-admin/analytics", "icon": "FiBarChart2", "category": "Insights", "keywords": ["reports", "metrics"]},
    {"title": "Audit Logs", "subtitle": "System audit trail", "path": "/super-admin/audit-logs", "icon": "FiShield", "category": "Insights", "keywords": ["security", "history"]},
    {"title": "Broadcast", "subtitle": "Send platform-wide messages", "path": "/super-admin/broadcast", "icon": "FiRadio", "category": "Communication", "keywords": ["announce", "message"]},
    {"title": "Settings", "subtitle": "Platform configuration", "path": "/super-admin/settings", "icon": "FiSettings", "category": "System", "keywords": ["config", "preferences"]},
    {"title": "My Profile", "subtitle": "Your super admin profile", "path": "/super-admin/profile", "icon": "FiUser", "category": "Account", "keywords": ["account", "avatar", "photo"]},
]

COMMON_SCHOOL_ENTRIES: list[dict[str, Any]] = [
    {"title": "Dashboard", "subtitle": "Your role dashboard", "path": "/school-admin", "icon": "FiHome", "category": "Pages", "keywords": ["home", "overview"]},
    {"title": "My Profile", "subtitle": "Update your personal details", "path": "/school-admin/profile", "icon": "FiUser", "category": "Account", "keywords": ["account", "avatar", "photo"]},
    {"title": "Notifications", "subtitle": "Your notification inbox", "path": "/school-admin/notifications", "icon": "FiBell", "category": "Account", "keywords": ["alerts", "inbox"]},
]

SCHOOL_ADMIN_EXTRA_ENTRIES: list[dict[str, Any]] = [
    {"title": "School Settings", "subtitle": "School profile and branding", "path": "/school-admin/settings", "icon": "FiSettings", "category": "System", "keywords": ["config", "branding"]},
    {"title": "Permission Settings", "subtitle": "Role module permissions", "path": "/school-admin/settings/permissions", "icon": "FiShield", "category": "System", "keywords": ["rbac", "roles", "access"]},
    {"title": "Plans & Subscriptions", "subtitle": "Your school's subscription", "path": "/school-admin/settings/plans", "icon": "FiLayers", "category": "System", "keywords": ["billing", "upgrade"]},
]


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _score_match(query: str, *texts: str) -> int:
    if not query:
        return 0
    best = 0
    for raw in texts:
        text = (raw or "").lower()
        if not text:
            continue
        if text == query:
            best = max(best, 100)
        elif text.startswith(query):
            best = max(best, 80)
        elif query in text:
            best = max(best, 60)
        else:
            tokens = [t for t in re.split(r"[\s_/\-]+", text) if t]
            if any(t.startswith(query) or query in t for t in tokens):
                best = max(best, 40)
    return best


def _entry_result(
    entry: dict[str, Any],
    *,
    result_type: str,
    query: str,
    entry_id: str,
) -> dict[str, Any] | None:
    haystack = [
        entry.get("title", ""),
        entry.get("subtitle", ""),
        entry.get("label", ""),
        entry.get("feature_key", ""),
        entry.get("module_key", ""),
        entry.get("key", ""),
        *entry.get("keywords", []),
    ]
    score = _score_match(query, *haystack)
    if score <= 0:
        return None
    return {
        "id": entry_id,
        "type": result_type,
        "category": entry.get("category", "Results"),
        "title": entry.get("title") or entry.get("label", ""),
        "subtitle": entry.get("subtitle", ""),
        "path": entry.get("path", ""),
        "icon": entry.get("icon", "FiSearch"),
        "score": score,
    }


def _collect_navigation_results(user, query: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if user.role == UserRole.SUPER_ADMIN:
        for idx, entry in enumerate(SUPER_ADMIN_SEARCH_ENTRIES):
            item = _entry_result(entry, result_type="page", query=query, entry_id=f"page:sa:{idx}")
            if item:
                results.append(item)
        return results

    tenant = getattr(user, "tenant", None)
    if not tenant:
        return results

    base_path = "/school-admin"
    for idx, entry in enumerate(COMMON_SCHOOL_ENTRIES):
        item = _entry_result(entry, result_type="page", query=query, entry_id=f"page:common:{idx}")
        if item:
            results.append(item)

    if user_is_school_admin(user):
        for idx, entry in enumerate(SCHOOL_ADMIN_EXTRA_ENTRIES):
            item = _entry_result(entry, result_type="page", query=query, entry_id=f"page:admin:{idx}")
            if item:
                results.append(item)

    from apps.tenants.role_permissions import get_user_feature_permissions

    module_menu = get_user_module_menu(tenant, user)
    module_permissions = get_user_module_permissions(tenant, user)
    feature_permissions = get_user_feature_permissions(tenant, user)

    for module in module_menu:
        mod_entry = {
            "title": module.get("label", ""),
            "subtitle": f"{module.get('enabled_count', 0)} features available",
            "path": module.get("path", base_path),
            "icon": module.get("icon", "FiGrid"),
            "category": "Modules",
            "key": module.get("key", ""),
            "keywords": [module.get("key", ""), module.get("feature_key", "")],
        }
        item = _entry_result(
            mod_entry,
            result_type="module",
            query=query,
            entry_id=f"module:{module.get('key', '')}",
        )
        if item:
            results.append(item)

        for child in module.get("children", []):
            feature_key = child.get("feature_key", "")
            if not feature_permissions.get(feature_key, {}).get("can_read"):
                continue
            child_entry = {
                "title": child.get("label", ""),
                "subtitle": module.get("label", ""),
                "path": child.get("path", module.get("path", base_path)),
                "icon": child.get("icon", module.get("icon", "FiGrid")),
                "category": "Features",
                "feature_key": child.get("feature_key", ""),
                "keywords": [child.get("feature_key", ""), module.get("key", "")],
            }
            child_item = _entry_result(
                child_entry,
                result_type="feature",
                query=query,
                entry_id=f"feature:{child.get('feature_key', '')}",
            )
            if child_item:
                results.append(child_item)

    role = normalize_role(user.role)
    profile = get_role_profile(user)
    actions = filter_quick_actions(profile, module_permissions)
    for idx, action in enumerate(actions):
        action_entry = {
            "title": action.get("label", ""),
            "subtitle": "Quick action",
            "path": action.get("path", base_path),
            "icon": "FiZap",
            "category": "Quick Actions",
            "module_key": action.get("module_key", ""),
            "keywords": ["action", action.get("module_key", ""), role],
        }
        action_item = _entry_result(
            action_entry,
            result_type="action",
            query=query,
            entry_id=f"action:{role}:{idx}",
        )
        if action_item:
            results.append(action_item)

    return results


def _user_can_search_staff(tenant, user) -> bool:
    from apps.tenants.role_permissions import user_can_access_module

    return (
        user_is_school_admin(user)
        or user_can_access_module(tenant, user, "human_resource")
        or user_can_access_module(tenant, user, "core_management")
    )


def _user_can_search_students(tenant, user) -> bool:
    from apps.tenants.role_permissions import user_can_access_module

    return user_is_school_admin(user) or user_can_access_module(tenant, user, "core_management")


def _collect_record_results(user, query: str, *, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    tenant = getattr(user, "tenant", None)
    if not tenant or user.role == UserRole.SUPER_ADMIN:
        return results

    remaining = max(limit, 0)

    if remaining and _user_can_search_staff(tenant, user):
        from apps.staff.models import Staff

        staff_qs = Staff.objects.filter(tenant=tenant).filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(employee_id__icontains=query)
        )[:remaining]
        for staff in staff_qs:
            score = _score_match(
                query,
                staff.full_name,
                staff.email,
                staff.employee_id,
            )
            if score <= 0:
                continue
            path = (
                f"/school-admin/hr/staffs/{staff.id}"
                if user_is_school_admin(user) or _user_can_search_staff(tenant, user)
                else "/school-admin/staff"
            )
            results.append({
                "id": f"staff:{staff.id}",
                "type": "staff",
                "category": "People",
                "title": staff.full_name,
                "subtitle": f"Staff · {staff.employee_id} · {staff.designation}",
                "path": path,
                "icon": "FiBriefcase",
                "score": score + 10,
            })
        remaining = max(limit - len(results), 0)

    if remaining and _user_can_search_students(tenant, user):
        from apps.students.models import Student

        student_qs = Student.objects.filter(tenant=tenant).filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(admission_number__icontains=query)
            | Q(email__icontains=query)
        )[:remaining]
        for student in student_qs:
            score = _score_match(
                query,
                student.full_name if hasattr(student, "full_name") else f"{student.first_name} {student.last_name}",
                getattr(student, "admission_number", ""),
                getattr(student, "email", ""),
            )
            if score <= 0:
                continue
            results.append({
                "id": f"student:{student.id}",
                "type": "student",
                "category": "People",
                "title": getattr(student, "full_name", f"{student.first_name} {student.last_name}".strip()),
                "subtitle": f"Student · {getattr(student, 'admission_number', '')}",
                "path": "/school-admin/students",
                "icon": "FiUsers",
                "score": score + 5,
            })
        remaining = max(limit - len(results), 0)

    if remaining and _user_can_search_students(tenant, user):
        from apps.students.models import Parent

        parent_qs = Parent.objects.filter(tenant=tenant).filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )[:remaining]
        for parent in parent_qs:
            score = _score_match(
                query,
                parent.full_name if hasattr(parent, "full_name") else f"{parent.first_name} {parent.last_name}",
                parent.email,
                parent.phone,
            )
            if score <= 0:
                continue
            results.append({
                "id": f"parent:{parent.id}",
                "type": "parent",
                "category": "People",
                "title": getattr(parent, "full_name", f"{parent.first_name} {parent.last_name}".strip()),
                "subtitle": f"Parent · {parent.email}",
                "path": "/school-admin/students",
                "icon": "FiHeart",
                "score": score + 5,
            })

    return results


def search_portal(user, query: str, *, limit: int = 20) -> dict[str, Any]:
    normalized = _normalize_query(query)
    if len(normalized) < 2:
        return {"query": query, "results": [], "total": 0}

    nav_results = _collect_navigation_results(user, normalized)
    record_results = _collect_record_results(user, normalized, limit=limit)

    combined = nav_results + record_results
    seen_paths: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in sorted(combined, key=lambda r: (-r["score"], r["title"].lower())):
        path = item.get("path", "")
        dedupe_key = f"{item.get('type')}:{path}:{item.get('title')}"
        if dedupe_key in seen_paths:
            continue
        seen_paths.add(dedupe_key)
        deduped.append({
            k: v for k, v in item.items() if k != "score"
        })
        if len(deduped) >= limit:
            break

    return {
        "query": query,
        "results": deduped,
        "total": len(deduped),
    }