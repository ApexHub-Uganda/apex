"""School role module and sub-module (feature) permissions — plan ∩ admin-configured access."""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.core.constants import UserRole, normalize_role
from apps.subscriptions.module_registry import SCHOOL_MODULES, get_module_for_feature
from apps.tenants.models import SchoolRoleFeaturePermission, SchoolRoleModulePermission

TENANT_ROLE_PERMS_CACHE = "tenant:role_perms:{tenant_id}"
TENANT_ROLE_FEATURE_PERMS_CACHE = "tenant:role_feature_perms:{tenant_id}"
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
    cache.delete(TENANT_ROLE_FEATURE_PERMS_CACHE.format(tenant_id=tenant_id))


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


def _stored_feature_permissions_map(tenant) -> dict[str, dict[str, dict[str, bool]]]:
    key = TENANT_ROLE_FEATURE_PERMS_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    rows = SchoolRoleFeaturePermission.objects.filter(tenant=tenant)
    result: dict[str, dict[str, dict[str, bool]]] = {}
    for row in rows:
        role = normalize_role(row.role)
        result.setdefault(role, {})[row.feature_key] = {
            "can_read": row.can_read,
            "can_write": row.can_write,
        }

    cache.set(key, result, CACHE_TTL)
    return result


def _module_is_granular(
    stored_features: dict[str, dict[str, bool]],
    children: list[dict[str, Any]],
) -> bool:
    if not stored_features or not children:
        return False
    child_keys = {child["feature_key"] for child in children}
    return any(feature_key in stored_features for feature_key in child_keys)


def get_default_role_permissions(role: str) -> dict[str, dict[str, bool]]:
    canonical = normalize_role(role)
    return {
        module_key: perms.copy()
        for module_key, perms in DEFAULT_ROLE_MODULE_PERMISSIONS.get(canonical, {}).items()
    }


def get_effective_role_permissions(tenant, role: str) -> dict[str, dict[str, bool]]:
    """Merged defaults with tenant overrides for a single role (module level)."""
    canonical = normalize_role(role)
    effective = get_default_role_permissions(canonical)
    stored = _stored_permissions_map(tenant).get(canonical, {})
    for module_key, perms in stored.items():
        effective[module_key] = perms.copy()
    return effective


def get_effective_feature_permissions(tenant, role: str) -> dict[str, dict[str, bool]]:
    """Resolved sub-module permissions for a role (plan ∩ module ∩ feature overrides)."""
    from apps.subscriptions.services import get_tenant_module_menu

    canonical = normalize_role(role)
    module_perms = get_effective_role_permissions(tenant, canonical)
    stored_features = _stored_feature_permissions_map(tenant).get(canonical, {})
    plan_menu = get_tenant_module_menu(tenant)

    resolved: dict[str, dict[str, bool]] = {}
    for module in plan_menu:
        module_key = module["key"]
        mod_perms = module_perms.get(module_key, {"can_read": False, "can_write": False})
        children = module.get("children", [])
        granular = _module_is_granular(stored_features, children)

        for child in children:
            feature_key = child["feature_key"]
            if not mod_perms.get("can_read"):
                resolved[feature_key] = {"can_read": False, "can_write": False}
                continue

            if granular:
                feat = stored_features.get(
                    feature_key,
                    {"can_read": False, "can_write": False},
                )
                resolved[feature_key] = {
                    "can_read": bool(feat.get("can_read")),
                    "can_write": bool(feat.get("can_write")) and bool(mod_perms.get("can_write")),
                }
            else:
                resolved[feature_key] = {
                    "can_read": bool(mod_perms.get("can_read")),
                    "can_write": bool(mod_perms.get("can_write")),
                }

    return resolved


def user_is_school_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
    )


def get_user_module_permissions(tenant, user) -> dict[str, dict[str, bool]]:
    """Effective module permissions derived from feature access when granular."""
    if user_is_school_admin(user):
        from apps.subscriptions.services import get_tenant_module_menu

        return {
            module["key"]: {"can_read": True, "can_write": True}
            for module in get_tenant_module_menu(tenant)
        }

    feature_perms = get_user_feature_permissions(tenant, user)
    from apps.subscriptions.services import get_tenant_module_menu

    module_permissions: dict[str, dict[str, bool]] = {}
    for module in get_tenant_module_menu(tenant):
        module_key = module["key"]
        children = module.get("children", [])
        readable_children = [
            child for child in children
            if feature_perms.get(child["feature_key"], {}).get("can_read")
        ]
        if not readable_children:
            continue
        writable = any(
            feature_perms.get(child["feature_key"], {}).get("can_write")
            for child in readable_children
        )
        module_permissions[module_key] = {
            "can_read": True,
            "can_write": writable,
        }
    return module_permissions


def get_user_feature_permissions(tenant, user) -> dict[str, dict[str, bool]]:
    if user_is_school_admin(user):
        from apps.subscriptions.services import get_tenant_module_menu

        result: dict[str, dict[str, bool]] = {}
        for module in get_tenant_module_menu(tenant):
            for child in module.get("children", []):
                result[child["feature_key"]] = {"can_read": True, "can_write": True}
        return result
    return get_effective_feature_permissions(tenant, user.role)


def filter_module_menu_by_role(
    plan_module_menu: list[dict[str, Any]],
    module_permissions: dict[str, dict[str, bool]],
    feature_permissions: dict[str, dict[str, bool]] | None = None,
) -> list[dict[str, Any]]:
    """Intersect plan modules with role permissions; hide ungranted sub-modules."""
    filtered: list[dict[str, Any]] = []
    for module in plan_module_menu:
        module_key = module["key"]
        perms = module_permissions.get(module_key, {})
        if not perms.get("can_read"):
            continue

        children: list[dict[str, Any]] = []
        for child in module.get("children", []):
            feature_key = child["feature_key"]
            if feature_permissions is not None:
                feat_perms = feature_permissions.get(feature_key, {})
                if not feat_perms.get("can_read"):
                    continue
                child_write = bool(feat_perms.get("can_write"))
            else:
                child_write = bool(perms.get("can_write"))

            children.append({
                **child,
                "can_read": True,
                "can_write": child_write,
            })

        if not children:
            continue

        can_write = bool(perms.get("can_write")) or any(c.get("can_write") for c in children)
        filtered.append({
            **module,
            "can_read": True,
            "can_write": can_write,
            "children": children,
            "enabled_count": len(children),
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

    feature_permissions = get_user_feature_permissions(tenant, user)
    module_permissions = get_user_module_permissions(tenant, user)
    return filter_module_menu_by_role(plan_menu, module_permissions, feature_permissions)


def permissions_to_strings(
    module_permissions: dict[str, dict[str, bool]],
    feature_permissions: dict[str, dict[str, bool]] | None = None,
) -> list[str]:
    tokens: list[str] = []
    for module_key, perms in module_permissions.items():
        if perms.get("can_read"):
            tokens.append(f"{module_key}.read")
        if perms.get("can_write"):
            tokens.append(f"{module_key}.write")
    if feature_permissions:
        for feature_key, perms in feature_permissions.items():
            if perms.get("can_read"):
                tokens.append(f"{feature_key}.read")
            if perms.get("can_write"):
                tokens.append(f"{feature_key}.write")
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


def user_can_access_feature(
    tenant,
    user,
    feature_key: str,
    *,
    require_write: bool = False,
) -> bool:
    if not feature_key:
        return True
    from apps.subscriptions.services import get_enabled_feature_keys

    if feature_key not in get_enabled_feature_keys(tenant):
        return False
    if user_is_school_admin(user):
        return True

    perms = get_user_feature_permissions(tenant, user).get(feature_key, {})
    if require_write:
        return bool(perms.get("can_write"))
    return bool(perms.get("can_read"))


def _delete_feature_permissions_for_module(tenant, role: str, module_key: str) -> int:
    from apps.subscriptions.services import get_tenant_module_menu

    child_keys = {
        child["feature_key"]
        for module in get_tenant_module_menu(tenant)
        if module["key"] == module_key
        for child in module.get("children", [])
    }
    if not child_keys:
        return 0
    deleted, _ = SchoolRoleFeaturePermission.objects.filter(
        tenant=tenant,
        role=normalize_role(role),
        feature_key__in=child_keys,
    ).delete()
    return deleted


def get_role_permission_matrix(tenant) -> dict[str, Any]:
    """Full matrix for school-admin permission settings UI (modules + sub-modules)."""
    from apps.subscriptions.services import get_tenant_module_menu

    plan_menu = get_tenant_module_menu(tenant)
    plan_modules = {m["key"] for m in plan_menu}
    stored_modules = _stored_permissions_map(tenant)
    stored_features = _stored_feature_permissions_map(tenant)

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
        custom_modules = stored_modules.get(canonical, {})
        custom_features = stored_features.get(canonical, {})

        for module in plan_menu:
            module_key = module["key"]
            if module_key not in plan_modules:
                continue

            default = defaults.get(module_key, {"can_read": False, "can_write": False})
            current = custom_modules.get(module_key, default)
            children = module.get("children", [])
            granular = _module_is_granular(custom_features, children)

            feature_cells: dict[str, dict[str, Any]] = {}
            for child in children:
                feature_key = child["feature_key"]
                if granular:
                    feat_current = custom_features.get(
                        feature_key,
                        {"can_read": False, "can_write": False},
                    )
                    feat_default = {
                        "can_read": current.get("can_read", False),
                        "can_write": current.get("can_write", False),
                    }
                else:
                    feat_current = {
                        "can_read": current.get("can_read", False),
                        "can_write": current.get("can_write", False),
                    }
                    feat_default = feat_current.copy()

                feature_cells[feature_key] = {
                    "label": child.get("label", feature_key.replace("_", " ").title()),
                    "icon": child.get("icon", module.get("icon", "FiGrid")),
                    "path": child.get("path", module.get("path", "")),
                    "can_read": bool(feat_current.get("can_read")),
                    "can_write": bool(feat_current.get("can_write")),
                    "is_custom": granular and feature_key in custom_features,
                    "default_read": bool(feat_default.get("can_read")),
                    "default_write": bool(feat_default.get("can_write")),
                }

            matrix[canonical][module_key] = {
                "can_read": bool(current.get("can_read")),
                "can_write": bool(current.get("can_write")),
                "is_custom": module_key in custom_modules,
                "default_read": bool(default.get("can_read")),
                "default_write": bool(default.get("can_write")),
                "granular": granular,
                "features": feature_cells,
            }

    return {
        "roles": roles_out,
        "modules": plan_menu,
        "matrix": matrix,
    }


@transaction.atomic
def save_role_permissions(
    tenant,
    permissions: list[dict[str, Any]],
    *,
    actor=None,
) -> dict[str, Any]:
    """Persist tenant role module and sub-module permission overrides."""
    from apps.subscriptions.services import get_tenant_module_menu

    plan_modules = {m["key"] for m in get_tenant_module_menu(tenant)}
    plan_features = {
        child["feature_key"]
        for module in get_tenant_module_menu(tenant)
        for child in module.get("children", [])
    }
    valid_roles = {normalize_role(r) for r in UserRole.CONFIGURABLE_ROLES}

    module_entries = [p for p in permissions if p.get("module_key") and not p.get("feature_key")]
    feature_entries = [p for p in permissions if p.get("feature_key")]
    module_write_by_role: dict[str, dict[str, bool]] = {}

    for entry in module_entries:
        role = normalize_role(entry.get("role", ""))
        module_key = entry.get("module_key", "")
        if role not in valid_roles or module_key not in plan_modules:
            continue

        can_read = bool(entry.get("can_read"))
        can_write = bool(entry.get("can_write"))
        if can_write and not can_read:
            can_read = True

        if not can_read:
            _delete_feature_permissions_for_module(tenant, role, module_key)

        SchoolRoleModulePermission.objects.update_or_create(
            tenant=tenant,
            role=role,
            module_key=module_key,
            defaults={
                "can_read": can_read,
                "can_write": can_write,
            },
        )
        module_write_by_role.setdefault(role, {})[module_key] = can_write

        if entry.get("clear_granular"):
            _delete_feature_permissions_for_module(tenant, role, module_key)

    for entry in feature_entries:
        role = normalize_role(entry.get("role", ""))
        feature_key = entry.get("feature_key", "")
        if role not in valid_roles or feature_key not in plan_features:
            continue

        module = get_module_for_feature(feature_key)
        module_key = module["key"] if module else None
        if not module_key or module_key not in plan_modules:
            continue

        can_read = bool(entry.get("can_read"))
        can_write = bool(entry.get("can_write"))
        if can_write and not can_read:
            can_read = True

        if module_key:
            mod_write = module_write_by_role.get(role, {}).get(module_key)
            if mod_write is None:
                mod_write = get_effective_role_permissions(tenant, role).get(
                    module_key, {},
                ).get("can_write", False)
            if not mod_write:
                can_write = False

        if not can_read and not can_write:
            SchoolRoleFeaturePermission.objects.filter(
                tenant=tenant,
                role=role,
                feature_key=feature_key,
            ).delete()
            continue

        SchoolRoleFeaturePermission.objects.update_or_create(
            tenant=tenant,
            role=role,
            feature_key=feature_key,
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
    module_qs = SchoolRoleModulePermission.objects.filter(tenant=tenant)
    feature_qs = SchoolRoleFeaturePermission.objects.filter(tenant=tenant)
    if role:
        canonical = normalize_role(role)
        module_qs = module_qs.filter(role=canonical)
        feature_qs = feature_qs.filter(role=canonical)
    module_qs.delete()
    feature_qs.delete()
    invalidate_role_permissions_cache(str(tenant.id))
    return get_role_permission_matrix(tenant)