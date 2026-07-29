"""Dual portal roles — grant extra roles and switch active role.

Candidates include:
  - All school portal Users (staff + parents + other roles)
  - Parent directory rows (with or without a linked portal User)
  - Staff directory rows without a portal User (if any)

Granting dual roles never invents a second email/login when a User already exists.
Parents without a portal account get one created (temp password, must change).
"""
from __future__ import annotations

import secrets
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserRoleAssignment
from apps.core.constants import UserRole, normalize_role


class DualRoleError(Exception):
    def __init__(self, message: str, *, code: str = "dual_role_error"):
        self.message = message
        self.code = code
        super().__init__(message)


# Roles school admins may grant as dual roles (not super_admin / student)
DUAL_ROLE_CHOICES = [
    r for r in UserRole.SCHOOL_PORTAL_ROLES
    if r not in {UserRole.SUPER_ADMIN, UserRole.STUDENT}
]


def ensure_primary_assignment(user: User, *, actor=None) -> UserRoleAssignment | None:
    """
    Ensure the user's current active role has a primary assignment row.

    Important: never re-activate a dual-role assignment that was intentionally
    revoked (is_active=False). Doing so made the first revoke look like a no-op.
    """
    if not user or not user.tenant_id or not user.role:
        return None
    if user.role == UserRole.SUPER_ADMIN:
        return None
    role = normalize_role(user.role)

    existing = UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, role=role,
    ).first()

    if existing is not None and not existing.is_active:
        # This role was revoked — do not resurrect it. Prefer another active role.
        active = (
            UserRoleAssignment.objects.filter(
                user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
            ).first()
            or UserRoleAssignment.objects.filter(
                user=user, tenant_id=user.tenant_id, is_active=True,
            ).first()
        )
        if active:
            if not active.is_primary:
                UserRoleAssignment.objects.filter(
                    user=user, tenant_id=user.tenant_id, is_active=True,
                ).update(is_primary=False)
                active.is_primary = True
                active.save(update_fields=["is_primary", "updated_at"])
            return active
        return None

    if existing is None:
        assignment = UserRoleAssignment.objects.create(
            user=user,
            tenant_id=user.tenant_id,
            role=role,
            is_primary=True,
            is_active=True,
            source="system",
            granted_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, is_active=True,
        ).exclude(pk=assignment.pk).update(is_primary=False)
        return assignment

    # existing is active
    if not UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
    ).exists():
        existing.is_primary = True
        existing.save(update_fields=["is_primary", "updated_at"])
    return existing


def _active_assignment_roles(user: User) -> list[str]:
    """Active dual-role assignments only (no auto-heal side effects)."""
    if not user or not user.tenant_id:
        return []
    roles = list(
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, is_active=True,
        ).values_list("role", flat=True)
    )
    seen: set[str] = set()
    out: list[str] = []
    for r in roles:
        nr = normalize_role(r)
        if nr and nr not in seen and nr != UserRole.SUPER_ADMIN:
            seen.add(nr)
            out.append(nr)
    return out


def list_user_roles(user: User) -> list[str]:
    """Active roles the user may switch into."""
    if not user:
        return []
    if not user.tenant_id:
        return [normalize_role(user.role)] if user.role else []

    ensure_primary_assignment(user)
    roles = _active_assignment_roles(user)

    # Legacy users with no assignment rows yet: expose User.role once.
    # Never re-add a role that has an inactive (revoked) assignment.
    current = normalize_role(user.role)
    if current and current not in roles:
        revoked = UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, role=current, is_active=False,
        ).exists()
        any_assignment = UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id,
        ).exists()
        if not revoked and not any_assignment:
            roles.append(current)

    return roles


def role_payload(user: User) -> dict[str, Any]:
    roles = list_user_roles(user)
    primary = (
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
        ).values_list("role", flat=True).first()
        if user.tenant_id
        else None
    )
    primary = normalize_role(primary or user.role)
    return {
        "active_role": normalize_role(user.role),
        "primary_role": primary,
        "available_roles": roles,
        "can_switch_role": len(roles) > 1,
        "role_labels": {
            r: dict(UserRole.CHOICES).get(r, r.replace("_", " ").title()) for r in roles
        },
    }


def _safe_staff(user: User):
    try:
        staff = user.staff_profile
        if staff and getattr(staff, "is_deleted", False):
            return None
        return staff
    except Exception:
        return None


def _safe_parent(user: User):
    try:
        parent = user.parent_profile
        if parent and getattr(parent, "is_deleted", False):
            return None
        return parent
    except Exception:
        return None


def is_staff_like_role(role: str) -> bool:
    role = normalize_role(role)
    return role in UserRole.STAFF_ROLES or role == UserRole.SCHOOL_ADMIN


def dual_identity_for_user(user: User | None) -> dict[str, Any]:
    """
    Canonical identity flags used by parent/staff directories and profile UIs.
    One User may own both a Staff row and a Parent row.
    """
    if not user:
        return {
            "user_id": None,
            "available_roles": [],
            "is_dual_role": False,
            "has_staff_profile": False,
            "has_parent_profile": False,
            "also_staff": False,
            "also_parent": False,
        }
    roles = list_user_roles(user)
    staff = _safe_staff(user)
    parent = _safe_parent(user)
    has_staff = staff is not None or any(is_staff_like_role(r) for r in roles)
    has_parent = parent is not None or UserRole.PARENT in roles
    return {
        "user_id": str(user.id),
        "available_roles": roles,
        "is_dual_role": len(roles) > 1,
        "has_staff_profile": staff is not None,
        "has_parent_profile": parent is not None,
        "also_staff": has_staff and has_parent,
        "also_parent": has_staff and has_parent,
        "active_role": normalize_role(user.role),
        "role_labels": {
            r: dict(UserRole.CHOICES).get(r, r.replace("_", " ").title()) for r in roles
        },
    }


def search_dual_role_candidates(*, tenant, q: str = "", limit: int = 60) -> list[dict[str, Any]]:
    """
    Unified search: portal Users (staff + parents + …) and Parent/Staff directory
    rows that may not yet have a portal login.
    """
    from apps.staff.models import Staff
    from apps.students.models import Parent

    q = (q or "").strip()
    results: list[dict[str, Any]] = []
    seen_user_ids: set = set()
    seen_emails: set[str] = set()

    def _note_email(email: str | None) -> None:
        if email:
            seen_emails.add(email.strip().lower())

    # ── 1) Portal users (all school roles except super_admin / student) ──
    uqs = (
        User.objects.filter(tenant=tenant, is_active=True)
        .exclude(role__in=[UserRole.SUPER_ADMIN, UserRole.STUDENT])
        .select_related("tenant")
        .order_by("last_name", "first_name")
    )
    if q:
        uqs = uqs.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
        )
    for u in uqs[:limit]:
        ensure_primary_assignment(u)
        payload = role_payload(u)
        staff = _safe_staff(u)
        parent = _safe_parent(u)
        results.append({
            "id": str(u.id),
            "source": "user",
            "user_id": str(u.id),
            "parent_id": str(parent.id) if parent else None,
            "staff_id": str(staff.id) if staff else None,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone or "",
            "active_role": payload["active_role"],
            "primary_role": payload["primary_role"],
            "available_roles": payload["available_roles"],
            "role_labels": payload["role_labels"],
            "has_staff_profile": staff is not None,
            "has_parent_profile": parent is not None,
            "needs_portal_account": False,
            "directory": "staff" if staff else ("parent" if parent or normalize_role(u.role) == UserRole.PARENT else "user"),
        })
        seen_user_ids.add(u.id)
        _note_email(u.email)

    # ── 2) Parent directory (include those without portal User) ──
    remaining = max(0, limit - len(results))
    if remaining:
        pqs = Parent.objects.filter(tenant=tenant, is_deleted=False).select_related("user")
        if q:
            pqs = pqs.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(middle_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(alternate_phone__icontains=q)
            )
        for p in pqs.order_by("last_name", "first_name")[: remaining + 20]:
            if p.user_id and p.user_id in seen_user_ids:
                continue
            email_key = (p.email or "").strip().lower()
            # If parent email already listed as a User, skip duplicate card
            if email_key and email_key in seen_emails and not p.user_id:
                continue
            if p.user_id:
                u = p.user
                if u and u.is_active and u.id not in seen_user_ids:
                    ensure_primary_assignment(u)
                    payload = role_payload(u)
                    staff = _safe_staff(u)
                    results.append({
                        "id": str(u.id),
                        "source": "user",
                        "user_id": str(u.id),
                        "parent_id": str(p.id),
                        "staff_id": str(staff.id) if staff else None,
                        "email": u.email,
                        "full_name": u.full_name or p.full_name,
                        "phone": u.phone or p.phone or "",
                        "active_role": payload["active_role"],
                        "primary_role": payload["primary_role"],
                        "available_roles": payload["available_roles"],
                        "role_labels": payload["role_labels"],
                        "has_staff_profile": staff is not None,
                        "has_parent_profile": True,
                        "needs_portal_account": False,
                        "directory": "parent",
                    })
                    seen_user_ids.add(u.id)
                    _note_email(u.email)
                continue

            # Parent row without portal login
            labels = {UserRole.PARENT: dict(UserRole.CHOICES).get(UserRole.PARENT, "Parent")}
            results.append({
                "id": f"parent:{p.id}",
                "source": "parent",
                "user_id": None,
                "parent_id": str(p.id),
                "staff_id": None,
                "email": p.email or "",
                "full_name": p.full_name,
                "phone": p.phone or "",
                "active_role": UserRole.PARENT,
                "primary_role": UserRole.PARENT,
                "available_roles": [UserRole.PARENT],
                "role_labels": labels,
                "has_staff_profile": False,
                "has_parent_profile": True,
                "needs_portal_account": True,
                "directory": "parent",
            })
            _note_email(p.email)
            if len(results) >= limit:
                break

    # ── 3) Staff directory without portal User (rare) ──
    remaining = max(0, limit - len(results))
    if remaining:
        sqs = Staff.objects.filter(tenant=tenant, is_deleted=False, user__isnull=True)
        if q:
            sqs = sqs.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(employee_id__icontains=q)
            )
        for s in sqs.order_by("last_name", "first_name")[:remaining]:
            email_key = (s.email or "").strip().lower()
            if email_key and email_key in seen_emails:
                continue
            role = normalize_role(s.portal_role or UserRole.TEACHER)
            labels = {role: dict(UserRole.CHOICES).get(role, role)}
            results.append({
                "id": f"staff:{s.id}",
                "source": "staff",
                "user_id": None,
                "parent_id": None,
                "staff_id": str(s.id),
                "email": s.email or "",
                "full_name": s.full_name,
                "phone": s.phone or "",
                "active_role": role,
                "primary_role": role,
                "available_roles": [role],
                "role_labels": labels,
                "has_staff_profile": True,
                "has_parent_profile": False,
                "needs_portal_account": True,
                "directory": "staff",
            })
            _note_email(s.email)

    # Prefer parents and multi-role users when sorting for empty search? Keep order mixed:
    # users first (as queried), then parents, then staff orphans.
    return results[:limit]


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(10)


@transaction.atomic
def resolve_or_create_user_for_candidate(
    *,
    tenant,
    actor=None,
    user_id: str | None = None,
    parent_id: str | None = None,
    staff_id: str | None = None,
) -> tuple[User, bool, str | None]:
    """
    Resolve a dual-role target to a portal User.

    Returns (user, created_new_account, temp_password_or_none).
    """
    from apps.staff.models import Staff
    from apps.students.models import Parent

    if user_id:
        user = User.objects.filter(pk=user_id, tenant=tenant, is_active=True).first()
        if not user:
            raise DualRoleError("User not found in this school.", code="user_not_found")
        ensure_primary_assignment(user, actor=actor)
        return user, False, None

    if parent_id:
        parent = Parent.objects.filter(pk=parent_id, tenant=tenant, is_deleted=False).select_related("user").first()
        if not parent:
            raise DualRoleError("Parent record not found.", code="parent_not_found")
        if parent.user_id and parent.user and parent.user.is_active:
            ensure_primary_assignment(parent.user, actor=actor)
            return parent.user, False, None

        email = (parent.email or "").strip().lower()
        if not email:
            raise DualRoleError(
                "This parent has no email. Add an email on the parent record before dual roles.",
                code="parent_no_email",
            )

        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            if existing.tenant_id and str(existing.tenant_id) != str(tenant.id):
                raise DualRoleError(
                    "This parent email is already used by a portal account at another school.",
                    code="email_other_tenant",
                )
            # Link existing same-tenant (or untenanted) user
            if existing.tenant_id is None:
                existing.tenant = tenant
                existing.save(update_fields=["tenant", "updated_at"])
            parent.user = existing
            parent.has_portal_access = True
            parent.save(update_fields=["user", "has_portal_access", "updated_at"])
            ensure_primary_assignment(existing, actor=actor)
            # Ensure parent role assignment exists
            grant_roles(user=existing, roles=[UserRole.PARENT], actor=actor)
            return existing, False, None

        temp = _generate_temp_password()
        user = User.objects.create_user(
            email=email,
            password=temp,
            first_name=parent.first_name or "Parent",
            last_name=parent.last_name or "User",
            phone=parent.phone or "",
            role=UserRole.PARENT,
            tenant=tenant,
            is_active=True,
            is_email_verified=False,
            must_change_password=True,
        )
        parent.user = user
        parent.has_portal_access = True
        parent.save(update_fields=["user", "has_portal_access", "updated_at"])
        ensure_primary_assignment(user, actor=actor)
        return user, True, temp

    if staff_id:
        staff = Staff.objects.filter(pk=staff_id, tenant=tenant, is_deleted=False).select_related("user").first()
        if not staff:
            raise DualRoleError("Staff record not found.", code="staff_not_found")
        if staff.user_id and staff.user and staff.user.is_active:
            ensure_primary_assignment(staff.user, actor=actor)
            return staff.user, False, None

        email = (staff.email or "").strip().lower()
        if not email:
            raise DualRoleError(
                "This staff member has no work email. Add one before enabling dual roles.",
                code="staff_no_email",
            )
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            if existing.tenant_id and str(existing.tenant_id) != str(tenant.id):
                raise DualRoleError(
                    "This staff email is already used by a portal account at another school.",
                    code="email_other_tenant",
                )
            if existing.tenant_id is None:
                existing.tenant = tenant
                existing.save(update_fields=["tenant", "updated_at"])
            staff.user = existing
            staff.has_portal_access = True
            staff.save(update_fields=["user", "has_portal_access", "updated_at"])
            ensure_primary_assignment(existing, actor=actor)
            return existing, False, None

        role = normalize_role(staff.portal_role or UserRole.TEACHER)
        temp = _generate_temp_password()
        user = User.objects.create_user(
            email=email,
            password=temp,
            first_name=staff.first_name or "Staff",
            last_name=staff.last_name or "Member",
            phone=staff.phone or "",
            role=role,
            tenant=tenant,
            is_active=True,
            must_change_password=True,
        )
        staff.user = user
        staff.has_portal_access = True
        staff.save(update_fields=["user", "has_portal_access", "updated_at"])
        ensure_primary_assignment(user, actor=actor)
        return user, True, temp

    raise DualRoleError("Provide user_id, parent_id, or staff_id.", code="target_required")


@transaction.atomic
def grant_roles(
    *,
    user: User,
    roles: list[str],
    actor=None,
    set_active: str | None = None,
) -> dict[str, Any]:
    """
    Grant additional dual roles to *user*.

    Existing roles stay; already-held roles are ignored (not duplicated).
    Does **not** reset password for existing accounts.
    """
    if not user.tenant_id:
        raise DualRoleError("User has no school tenant.", code="no_tenant")
    if user.role == UserRole.SUPER_ADMIN:
        raise DualRoleError("Cannot assign dual roles to a super admin.", code="super_admin")

    ensure_primary_assignment(user, actor=actor)
    existing = set(list_user_roles(user))
    # Ensure native directory rows exist for every role already held (one person, many lists)
    for held in list(existing):
        _ensure_profile_for_role(user, held, actor=actor)
    added: list[str] = []

    for raw in roles or []:
        role = normalize_role(raw)
        if not role or role in {UserRole.SUPER_ADMIN, UserRole.STUDENT}:
            continue
        if role not in DUAL_ROLE_CHOICES and role != UserRole.SCHOOL_ADMIN:
            if role not in UserRole.SCHOOL_PORTAL_ROLES:
                raise DualRoleError(f"Role “{role}” cannot be dual-assigned.", code="invalid_role")
        if role in existing:
            continue
        UserRoleAssignment.objects.create(
            user=user,
            tenant_id=user.tenant_id,
            role=role,
            is_primary=False,
            is_active=True,
            source="admin",
            granted_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
        added.append(role)
        existing.add(role)
        _ensure_profile_for_role(user, role, actor=actor)

    if set_active:
        target = normalize_role(set_active)
        if target in existing:
            switch_role(user=user, role=target, actor=actor)

    return {
        "user_id": str(user.id),
        "added_roles": added,
        "available_roles": list_user_roles(user),
        "credentials_reused": True,
        "message": (
            f"Dual role(s) granted: {', '.join(added)}. "
            "They sign in with the same email and password; use Switch role from the avatar menu."
            if added
            else "No new roles added (selected roles already granted)."
        ),
    }


@transaction.atomic
def grant_roles_to_candidate(
    *,
    tenant,
    actor=None,
    roles: list[str],
    user_id: str | None = None,
    parent_id: str | None = None,
    staff_id: str | None = None,
) -> dict[str, Any]:
    """High-level grant used by admin API — works for users, parents, and staff rows."""
    user, created, temp_password = resolve_or_create_user_for_candidate(
        tenant=tenant,
        actor=actor,
        user_id=user_id,
        parent_id=parent_id,
        staff_id=staff_id,
    )
    data = grant_roles(user=user, roles=roles, actor=actor)
    data["portal_account_created"] = created
    data["credentials_reused"] = not created
    data["identity"] = dual_identity_for_user(user)
    # Convenience for admin UIs / tests
    data["has_staff_profile"] = data["identity"]["has_staff_profile"]
    data["has_parent_profile"] = data["identity"]["has_parent_profile"]
    if created and temp_password:
        data["temporary_password"] = temp_password
        data["message"] = (
            (data.get("message") or "")
            + f" A new portal login was created for {user.email}. "
            f"Temporary password: {temp_password} (user must change it on first login)."
        ).strip()
        # Best-effort credentials email
        try:
            from apps.staff.portal_credentials import send_staff_portal_credentials_email

            send_staff_portal_credentials_email(
                user=user,
                tenant=tenant,
                temp_password=temp_password,
            )
            data["credentials_emailed"] = True
        except Exception:
            data["credentials_emailed"] = False
    return data


def _ensure_profile_for_role(user: User, role: str, *, actor=None) -> None:
    """Create or restore Parent/Staff directory rows so the person appears in native lists."""
    role = normalize_role(role)
    actor_ok = actor if getattr(actor, "is_authenticated", False) else None

    if role == UserRole.PARENT:
        from apps.students.models import Parent

        parent = _safe_parent(user)
        if parent is None:
            # Restore soft-deleted parent for this user if dual-role was revoked earlier
            parent = Parent.all_objects.filter(
                tenant_id=user.tenant_id, user=user,
            ).order_by("-updated_at").first()
            if parent and parent.is_deleted:
                parent.restore(user=actor_ok)
                parent.has_portal_access = True
                parent.first_name = parent.first_name or user.first_name or "Parent"
                parent.last_name = parent.last_name or user.last_name or "User"
                parent.email = parent.email or user.email
                parent.phone = parent.phone or user.phone or ""
                parent.save(update_fields=[
                    "has_portal_access", "first_name", "last_name", "email", "phone", "updated_at",
                ])
            else:
                parent = Parent.objects.filter(
                    tenant_id=user.tenant_id, email__iexact=user.email, is_deleted=False,
                ).first()
                if parent and (parent.user_id is None or parent.user_id == user.id):
                    parent.user = user
                    parent.has_portal_access = True
                    # Keep names in sync with the single person
                    parent.first_name = user.first_name or parent.first_name
                    parent.last_name = user.last_name or parent.last_name
                    parent.phone = parent.phone or user.phone or ""
                    parent.save(update_fields=[
                        "user", "has_portal_access", "first_name", "last_name", "phone", "updated_at",
                    ])
                elif parent is None:
                    Parent.objects.create(
                        tenant_id=user.tenant_id,
                        user=user,
                        first_name=user.first_name or "Parent",
                        last_name=user.last_name or "User",
                        email=user.email,
                        phone=user.phone or "",
                        has_portal_access=True,
                        created_by=actor_ok,
                        updated_by=actor_ok,
                    )
        else:
            updates = []
            if parent.user_id is None:
                parent.user = user
                updates.append("user")
            if not parent.has_portal_access:
                parent.has_portal_access = True
                updates.append("has_portal_access")
            # Single person — mirror name/phone from portal user when blank
            if user.first_name and parent.first_name in ("", "Parent"):
                parent.first_name = user.first_name
                updates.append("first_name")
            if user.last_name and parent.last_name in ("", "User"):
                parent.last_name = user.last_name
                updates.append("last_name")
            if updates:
                parent.updated_by = actor_ok
                updates.extend(["updated_at", "updated_by"])
                parent.save(update_fields=list(dict.fromkeys(updates)))
        return

    # Staff / teaching roles — ensure Staff + Teacher where needed
    if is_staff_like_role(role):
        from apps.staff.models import Staff, Teacher
        from apps.staff.staff_roles import get_role_definition, role_requires_teacher_profile

        staff = _safe_staff(user)
        if staff is None:
            staff = Staff.all_objects.filter(
                tenant_id=user.tenant_id, user=user,
            ).order_by("-updated_at").first()
            if staff and staff.is_deleted:
                staff.restore(user=actor_ok)
                staff.has_portal_access = True
                staff.portal_role = role
                staff.first_name = staff.first_name or user.first_name or "Staff"
                staff.last_name = staff.last_name or user.last_name or "Member"
                staff.email = staff.email or user.email
                staff.phone = staff.phone or user.phone or ""
                staff.save(update_fields=[
                    "has_portal_access", "portal_role", "first_name", "last_name",
                    "email", "phone", "updated_at",
                ])
            else:
                staff = Staff.objects.filter(
                    tenant_id=user.tenant_id, email__iexact=user.email, is_deleted=False,
                ).first()
                if staff and (staff.user_id is None or staff.user_id == user.id):
                    staff.user = user
                    staff.has_portal_access = True
                    if role in dict(UserRole.CHOICES):
                        staff.portal_role = role
                    staff.first_name = user.first_name or staff.first_name
                    staff.last_name = user.last_name or staff.last_name
                    staff.save(update_fields=[
                        "user", "has_portal_access", "portal_role",
                        "first_name", "last_name", "updated_at",
                    ])
                elif staff is None:
                    role_def = get_role_definition(role) if role != UserRole.SCHOOL_ADMIN else {
                        "category": "management",
                        "default_designation": "School Administrator",
                    }
                    base = (user.email.split("@")[0] or "EMP")[:20].upper()
                    emp_id = base
                    n = 1
                    while Staff.all_objects.filter(tenant_id=user.tenant_id, employee_id=emp_id).exists():
                        n += 1
                        emp_id = f"{base}{n}"
                    staff = Staff.objects.create(
                        tenant_id=user.tenant_id,
                        user=user,
                        employee_id=emp_id,
                        first_name=user.first_name or "Staff",
                        last_name=user.last_name or "Member",
                        email=user.email,
                        phone=user.phone or "",
                        portal_role=role if role != UserRole.SCHOOL_ADMIN else UserRole.SCHOOL_ADMIN,
                        staff_category=role_def.get("category", "administrative"),
                        designation=role_def.get("default_designation", "Staff"),
                        date_joined=timezone.localdate(),
                        has_portal_access=True,
                        created_by=actor_ok,
                        updated_by=actor_ok,
                    )
        else:
            # Align portal_role if empty or non-staff; otherwise keep existing staff role
            if is_staff_like_role(role) and not is_staff_like_role(staff.portal_role or ""):
                staff.portal_role = role
                staff.has_portal_access = True
                staff.save(update_fields=["portal_role", "has_portal_access", "updated_at"])

        if role_requires_teacher_profile(role) or role in {
            UserRole.TEACHER, UserRole.CLASS_TEACHER, UserRole.HEAD_OF_DEPARTMENT,
            UserRole.DIRECTOR_OF_STUDIES,
        }:
            teacher = Teacher.all_objects.filter(staff=staff).order_by("-updated_at").first()
            if teacher is None:
                Teacher.objects.create(
                    tenant_id=user.tenant_id,
                    staff=staff,
                    created_by=actor_ok,
                    updated_by=actor_ok,
                )
            elif getattr(teacher, "is_deleted", False):
                teacher.restore(user=actor_ok)


def preview_revoke_role(*, user: User, role: str) -> dict[str, Any]:
    """
    Describe what removing a dual role will clean up — used for admin warnings.
    """
    role = normalize_role(role)
    labels = dict(UserRole.CHOICES)
    current = list_user_roles(user)
    if role not in current:
        raise DualRoleError("That role is not assigned.", code="not_assigned")
    if len(current) <= 1:
        raise DualRoleError("Cannot remove the only role on this account.", code="last_role")

    remaining = [r for r in current if r != role]
    remaining_staff = [r for r in remaining if is_staff_like_role(r)]
    impact: dict[str, Any] = {
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": role,
        "role_label": labels.get(role, role),
        "remaining_roles": remaining,
        "remaining_role_labels": {r: labels.get(r, r) for r in remaining},
        "will_switch_active_role": normalize_role(user.role) == role,
        "new_active_role": remaining[0] if normalize_role(user.role) == role else normalize_role(user.role),
        "cleanup": [],
        "warnings": [],
        "linked_students": [],
        "linked_students_count": 0,
        "will_remove_parent_profile": False,
        "will_remove_staff_profile": False,
    }

    if role == UserRole.PARENT:
        parent = _safe_parent(user)
        if parent:
            children = list(parent.children.filter(is_deleted=False).order_by("last_name", "first_name")[:20])
            impact["linked_students"] = [
                {
                    "id": str(c.id),
                    "full_name": c.full_name,
                    "admission_number": c.admission_number,
                }
                for c in children
            ]
            impact["linked_students_count"] = parent.children.filter(is_deleted=False).count()
            impact["will_remove_parent_profile"] = True
            impact["cleanup"].append(
                "Parent/guardian directory record will be removed from the Parents list."
            )
            if impact["linked_students_count"]:
                impact["cleanup"].append(
                    f"{impact['linked_students_count']} learner link(s) will be unlinked "
                    "(students stay enrolled; only this guardian link is removed)."
                )
                impact["warnings"].append(
                    "Linked learners will no longer show this person as a parent/guardian."
                )
            impact["cleanup"].append("Parent portal access for this role ends immediately.")
        else:
            impact["cleanup"].append("Parent role assignment will be removed (no parent directory row found).")

    if is_staff_like_role(role):
        if not remaining_staff:
            staff = _safe_staff(user)
            impact["will_remove_staff_profile"] = staff is not None
            if staff:
                impact["cleanup"].append(
                    "Staff directory record will be removed from the Staff list "
                    "(this was the last staff portal role)."
                )
                impact["cleanup"].append(
                    "Teaching profile linked to this staff record will be retired if present."
                )
                impact["warnings"].append(
                    "Historical attendance/marks marked by this person remain; "
                    "they will no longer appear as active staff."
                )
            else:
                impact["cleanup"].append("Staff role assignment will be removed.")
        else:
            impact["cleanup"].append(
                f"Only the “{labels.get(role, role)}” assignment is removed. "
                f"Staff profile is kept for remaining role(s): "
                + ", ".join(labels.get(r, r) for r in remaining_staff)
            )

    if impact["will_switch_active_role"]:
        impact["warnings"].append(
            f"Their active session role is “{labels.get(role, role)}”; "
            f"it will switch to “{labels.get(impact['new_active_role'], impact['new_active_role'])}”."
        )

    impact["summary"] = (
        f"Remove “{impact['role_label']}” from {user.full_name}. "
        + (" ".join(impact["warnings"][:2]) if impact["warnings"] else "Directory records for this role will be cleaned up.")
    )
    return impact


def _cleanup_after_revoke(*, user: User, role: str, actor=None) -> dict[str, Any]:
    """Remove directory dependencies for a revoked dual role."""
    cleaned: dict[str, Any] = {
        "parent_removed": False,
        "students_unlinked": 0,
        "staff_removed": False,
        "teacher_removed": False,
    }
    actor_ok = actor if getattr(actor, "is_authenticated", False) else None
    remaining = list_user_roles(user)

    if role == UserRole.PARENT:
        parent = _safe_parent(user)
        if parent:
            count = parent.children.count()
            parent.children.clear()
            cleaned["students_unlinked"] = count
            # Keep user FK so re-grant can restore the same person row
            parent.has_portal_access = False
            parent.save(update_fields=["has_portal_access", "updated_at"])
            parent.soft_delete(user=actor_ok)
            cleaned["parent_removed"] = True

    if is_staff_like_role(role):
        remaining_staff = [r for r in remaining if is_staff_like_role(r)]
        staff = _safe_staff(user)
        if remaining_staff and staff:
            # Point portal_role at a remaining staff role
            preferred = remaining_staff[0]
            for candidate in (
                UserRole.SCHOOL_ADMIN, UserRole.HEAD_TEACHER, UserRole.DIRECTOR_OF_STUDIES,
                UserRole.HEAD_OF_DEPARTMENT, UserRole.CLASS_TEACHER, UserRole.TEACHER,
            ):
                if candidate in remaining_staff:
                    preferred = candidate
                    break
            if staff.portal_role != preferred:
                staff.portal_role = preferred
                staff.save(update_fields=["portal_role", "updated_at"])
        elif not remaining_staff and staff:
            from apps.staff.models import Teacher

            teacher = Teacher.objects.filter(staff=staff).first()
            if teacher:
                teacher.soft_delete(user=actor_ok)
                cleaned["teacher_removed"] = True
            # Keep user FK for clean re-grant restore; hide from active staff directory
            staff.has_portal_access = False
            staff.save(update_fields=["has_portal_access", "updated_at"])
            staff.soft_delete(user=actor_ok)
            cleaned["staff_removed"] = True

    return cleaned


@transaction.atomic
def revoke_role(*, user: User, role: str, actor=None, cleanup: bool = True) -> dict[str, Any]:
    """
    Remove a dual role and (by default) clean associated Parent/Staff directory rows
    when that role is no longer needed.

    Order matters: switch User.role off the revoked role *before* deactivating the
    assignment, so ensure_primary_assignment cannot resurrect the revoked role.
    """
    role = normalize_role(role)
    if not role:
        raise DualRoleError("Role is required.", code="role_required")

    impact = preview_revoke_role(user=user, role=role)

    qs = UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, role=role, is_active=True,
    )
    if not qs.exists():
        raise DualRoleError("That role is not assigned.", code="not_assigned")

    # Remaining roles from DB only (no ensure_primary side effects)
    remaining = [
        r for r in _active_assignment_roles(user) if normalize_role(r) != role
    ]
    if not remaining:
        raise DualRoleError("Cannot remove the only role on this account.", code="last_role")

    # 1) Move active portal context off the role being removed
    if normalize_role(user.role) == role:
        next_role = remaining[0]
        # Set role without going through list_user_roles (assignment still active)
        user.role = next_role
        if next_role == UserRole.PARENT:
            user.is_staff = False
        elif is_staff_like_role(next_role):
            user.is_staff = True
        user.save(update_fields=["role", "is_staff", "updated_at"])
        staff = _safe_staff(user)
        if staff is not None and is_staff_like_role(next_role) and staff.portal_role != next_role:
            staff.portal_role = next_role
            staff.save(update_fields=["portal_role", "updated_at"])

    # 2) Deactivate the revoked assignment (do not delete history row)
    qs.update(is_active=False, is_primary=False, updated_at=timezone.now())
    UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, role=role,
    ).update(is_primary=False, is_active=False)

    # 3) Ensure a primary among what remains
    if not UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
    ).exists():
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, role=remaining[0], is_active=True,
        ).update(is_primary=True)

    # Refresh so list_user_roles / ensure_primary see updated user.role
    user.refresh_from_db()

    cleanup_result: dict[str, Any] = {}
    if cleanup:
        cleanup_result = _cleanup_after_revoke(user=user, role=role, actor=actor)

    user.refresh_from_db()
    available = list_user_roles(user)
    # Hard guarantee: revoked role never survives the response payload
    available = [r for r in available if normalize_role(r) != role]

    return {
        "user_id": str(user.id),
        "revoked": role,
        "role_label": impact.get("role_label", role),
        "available_roles": available,
        "impact": impact,
        "cleanup": cleanup_result,
        "identity": dual_identity_for_user(user),
        "dual_role": {
            **role_payload(user),
            "available_roles": available,
        },
        "message": (
            f"Removed “{impact.get('role_label', role)}” from {user.full_name}. "
            + (
                "Parent directory entry and learner links were cleaned up. "
                if cleanup_result.get("parent_removed")
                else ""
            )
            + (
                "Staff directory entry was cleaned up. "
                if cleanup_result.get("staff_removed")
                else ""
            )
        ).strip(),
    }


@transaction.atomic
def switch_role(*, user: User, role: str, actor=None) -> User:
    """Set User.role to a granted dual role (active permission context)."""
    role = normalize_role(role)
    allowed = list_user_roles(user)
    if role not in allowed:
        raise DualRoleError(
            "You do not have that portal role. Ask your school admin to grant dual roles.",
            code="not_granted",
        )
    if normalize_role(user.role) == role:
        return user
    user.role = role
    if role == UserRole.SUPER_ADMIN:
        user.is_staff = True
    elif role in UserRole.STAFF_ROLES or role == UserRole.SCHOOL_ADMIN:
        user.is_staff = True
    elif role == UserRole.PARENT:
        user.is_staff = False
    else:
        user.is_staff = role in UserRole.STAFF_ROLES
    user.save(update_fields=["role", "is_staff", "updated_at"])

    staff = _safe_staff(user)
    if staff is not None and role != UserRole.PARENT and role in UserRole.SCHOOL_PORTAL_ROLES:
        if staff.portal_role != role:
            staff.portal_role = role
            staff.save(update_fields=["portal_role", "updated_at"])
    return user


def issue_tokens_for_user(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["role"] = user.role
    refresh["full_name"] = user.full_name
    if user.tenant_id:
        refresh["tenant_id"] = str(user.tenant_id)
        refresh["tenant_name"] = user.tenant.name if user.tenant else ""
    access = refresh.access_token
    access["email"] = user.email
    access["role"] = user.role
    access["full_name"] = user.full_name
    if user.tenant_id:
        access["tenant_id"] = str(user.tenant_id)
    return {
        "refresh": str(refresh),
        "access": str(access),
    }


def dual_role_options() -> list[dict[str, str]]:
    labels = dict(UserRole.CHOICES)
    return [
        {"role": r, "label": labels.get(r, r.replace("_", " ").title())}
        for r in DUAL_ROLE_CHOICES
    ]
