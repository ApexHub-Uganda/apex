"""School role module permissions — plan ∩ admin-configured role access."""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.core.constants import UserRole, normalize_role
from apps.subscriptions.module_registry import SCHOOL_MODULES
from apps.tenants.models import SchoolRoleModulePermission

TENANT_ROLE_PERMS_CACHE = "tenant:role_perms:{tenant_id}"
CACHE_TTL = 60

DEFAULT_ROLE_MODULE_PERMISSIONS: dict[str, dict[str, dict[str, bool]]] = {
    UserRole.HOSTEL_MANAGER: {
        "hostel": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.TRANSPORT_MANAGER: {
        "transport": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.HR_MANAGER: {
        "human_resource": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.INVENTORY_MANAGER: {
        "inventory": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.LIBRARIAN: {
        "library": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.BURSAR: {
        "finance": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.DIRECTOR_OF_STUDIES: {
        "academics": {"can_read": True, "can_write": True},
        "examinations": {"can_read": True, "can_write": True},
        "attendance": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.HEAD_TEACHER: {
        "core_management": {"can_read": True, "can_write": False},
        "academics": {"can_read": True, "can_write": True},
        "attendance": {"can_read": True, "can_write": True},
        "examinations": {"can_read": True, "can_write": True},
        "communication": {"can_read": True, "can_write": True},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.DEPUTY_HEAD_TEACHER: {
        "academics": {"can_read": True, "can_write": True},
        "attendance": {"can_read": True, "can_write": True},
        "examinations": {"can_read": True, "can_write": False},
        "communication": {"can_read": True, "can_write": False},
        "analytics": {"can_read": True, "can_write": False},
    },
    UserRole.TEACHER: {
        "academics": {"can_read": True, "can_write": True},
        "attendance": {"can_read": True, "can_write": True},
        "examinations": {"can_read": True, "can_write": False},
        "communication": {"can_read": True, "can_write": False},
    },
    UserRole.HEAD_OF_DEPARTMENT: {
        "academics": {"can_read": True, "can_write": True},
        "examinations": {"can_read": True, "can_write": True},
        "attendance": {"can_read": True, "can_write": False},
    },
    UserRole.PARENT: {
        "communication": {"can_read": True, "can_write": False},
        "finance": {"can_read": True, "can_write": False},
        "analytics": {"can_read": True, "can_write": False},
        "events": {"can_read": True, "can_write": False},
    },
}


def _module_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": module["key"],
            "label": module["label"],
            "icon": module["icon"],
            "sort_order": module["sort_order"],
        }
        for module in SCHOOL_MODULES
    ]


def _role_labels() -> dict[str, str]:
    return dict(UserRole.CHOICES)


def invalidate_role_permissions_cache(tenant_id: str) -> None:
    cache.delete(TENANT_ROLE_PERMS_CACHE.format(tenant_id=tenant_id))


def _stored_permissions_map(tenant) -> dict[str, dict[str, dict[str, bool]]]:
    key = TENANT_ROLE_PERMS_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    rows = SchoolRoleModulePermission.objects.filter(tenant=tenant)
    result: dict[str, dict[str, dict[str, bool]]] = {}
    for row in rows:
        role = normalize_role(row.role)
        result.setdefault(role, {})[row.module_key] = {
            "can_read": row.can_read,
            "can_write": row.can_write,
        }

    cache.set(key, result, CACHE_TTL)
    return result


def get_default_role_permissions(role: str) -> dict[str, dict[str, bool]]:
    canonical = normalize_role(role)
    return {
        module_key: perms.copy()
        for module_key, perms in DEFAULT_ROLE_MODULE_PERMISSIONS.get(canonical, {}).items()
    }


def get_effective_role_permissions(tenant, role: str) -> dict[str, dict[str, bool]]:
    """Merged defaults with tenant overrides for a single role."""
    canonical = normalize_role(role)
    effective = get_default_role_permissions(canonical)
    stored = _stored_permissions_map(tenant).get(canonical, {})
    for module_key, perms in stored.items():
        effective[module_key] = perms.copy()
    return effective


def user_is_school_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
    )


def get_user_module_permissions(tenant, user) -> dict[str, dict[str, bool]]:
    """Effective module permissions for a user (plan filtering applied separately)."""
    if user_is_school_admin(user):
        from apps.subscriptions.services import get_tenant_module_menu

        return {
            module["key"]: {"can_read": True, "can_write": True}
            for module in get_tenant_module_menu(tenant)
        }
    return get_effective_role_permissions(tenant, user.role)


def filter_module_menu_by_role(
    plan_module_menu: list[dict[str, Any]],
    module_permissions: dict[str, dict[str, bool]],
) -> list[dict[str, Any]]:
    """Intersect plan-enabled modules with role read permissions."""
    filtered: list[dict[str, Any]] = []
    for module in plan_module_menu:
        perms = module_permissions.get(module["key"], {})
        if not perms.get("can_read"):
            continue
        can_write = perms.get("can_write", False)
        filtered.append({
            **module,
            "can_read": True,
            "can_write": can_write,
            "children": [
                {**child, "can_read": True, "can_write": can_write}
                for child in module.get("children", [])
            ],
        })
    return filtered


def get_user_module_menu(tenant, user) -> list[dict[str, Any]]:
    from apps.subscriptions.services import get_tenant_module_menu

    plan_menu = get_tenant_module_menu(tenant)
    if user_is_school_admin(user):
        return [
            {**module, "can_read": True, "can_write": True}
            for module in plan_menu
        ]
    module_permissions = get_user_module_permissions(tenant, user)
    return filter_module_menu_by_role(plan_menu, module_permissions)


def permissions_to_strings(module_permissions: dict[str, dict[str, bool]]) -> list[str]:
    tokens: list[str] = []
    for module_key, perms in module_permissions.items():
        if perms.get("can_read"):
            tokens.append(f"{module_key}.read")
        if perms.get("can_write"):
            tokens.append(f"{module_key}.write")
    return sorted(tokens)


def user_can_access_module(tenant, user, module_key: str, *, require_write: bool = False) -> bool:
    if not module_key:
        return True
    from apps.subscriptions.services import get_tenant_module_menu

    plan_keys = {m["key"] for m in get_tenant_module_menu(tenant)}
    if module_key not in plan_keys:
        return False
    perms = get_user_module_permissions(tenant, user).get(module_key, {})
    if require_write:
        return bool(perms.get("can_write"))
    return bool(perms.get("can_read"))


def get_role_permission_matrix(tenant) -> dict[str, Any]:
    """Full matrix for school-admin permission settings UI."""
    from apps.subscriptions.services import get_tenant_module_menu

    plan_modules = {m["key"] for m in get_tenant_module_menu(tenant)}
    stored = _stored_permissions_map(tenant)
    roles_out: list[dict[str, Any]] = []
    matrix: dict[str, dict[str, dict[str, Any]]] = {}

    for role in UserRole.CONFIGURABLE_ROLES:
        canonical = normalize_role(role)
        if canonical in {r["key"] for r in roles_out}:
            continue
        roles_out.append({
            "key": canonical,
            "label": _role_labels().get(role, canonical.replace("_", " ").title()),
        })
        matrix[canonical] = {}
        defaults = get_default_role_permissions(canonical)
        custom = stored.get(canonical, {})
        for module in _module_catalog():
            if module["key"] not in plan_modules:
                continue
            default = defaults.get(module["key"], {"can_read": False, "can_write": False})
            current = custom.get(module["key"], default)
            matrix[canonical][module["key"]] = {
                "can_read": current.get("can_read", False),
                "can_write": current.get("can_write", False),
                "is_custom": module["key"] in custom,
                "default_read": default.get("can_read", False),
                "default_write": default.get("can_write", False),
            }

    plan_module_catalog = [
        m for m in _module_catalog() if m["key"] in plan_modules
    ]

    return {
        "roles": roles_out,
        "modules": plan_module_catalog,
        "matrix": matrix,
    }


@transaction.atomic
def save_role_permissions(
    tenant,
    permissions: list[dict[str, Any]],
    *,
    actor=None,
) -> dict[str, Any]:
    """Persist tenant role permission overrides."""
    from apps.subscriptions.services import get_tenant_module_menu

    plan_modules = {m["key"] for m in get_tenant_module_menu(tenant)}
    valid_roles = {normalize_role(r) for r in UserRole.CONFIGURABLE_ROLES}

    for entry in permissions:
        role = normalize_role(entry.get("role", ""))
        module_key = entry.get("module_key", "")
        if role not in valid_roles or module_key not in plan_modules:
            continue
        can_read = bool(entry.get("can_read"))
        can_write = bool(entry.get("can_write"))
        if can_write and not can_read:
            can_read = True

        SchoolRoleModulePermission.objects.update_or_create(
            tenant=tenant,
            role=role,
            module_key=module_key,
            defaults={
                "can_read": can_read,
                "can_write": can_write,
            },
        )

    invalidate_role_permissions_cache(str(tenant.id))
    return get_role_permission_matrix(tenant)


@transaction.atomic
def reset_role_permissions(tenant, role: str | None = None) -> dict[str, Any]:
    """Remove custom overrides (all roles or one role)."""
    qs = SchoolRoleModulePermission.objects.filter(tenant=tenant)
    if role:
        qs = qs.filter(role=normalize_role(role))
    qs.delete()
    invalidate_role_permissions_cache(str(tenant.id))
    return get_role_permission_matrix(tenant)