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
    """Ensure the user's current role is recorded as a primary assignment."""
    if not user or not user.tenant_id or not user.role:
        return None
    if user.role == UserRole.SUPER_ADMIN:
        return None
    role = normalize_role(user.role)
    assignment, created = UserRoleAssignment.objects.get_or_create(
        user=user,
        tenant_id=user.tenant_id,
        role=role,
        defaults={
            "is_primary": True,
            "is_active": True,
            "source": "system",
            "granted_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )
    if created:
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, is_active=True,
        ).exclude(pk=assignment.pk).update(is_primary=False)
        return assignment
    if not assignment.is_active:
        assignment.is_active = True
        assignment.save(update_fields=["is_active", "updated_at"])
    if not UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
    ).exists():
        assignment.is_primary = True
        assignment.save(update_fields=["is_primary", "updated_at"])
    return assignment


def list_user_roles(user: User) -> list[str]:
    """Active roles the user may switch into (includes current User.role)."""
    if not user:
        return []
    ensure_primary_assignment(user)
    if not user.tenant_id:
        return [normalize_role(user.role)] if user.role else []
    roles = list(
        UserRoleAssignment.objects.filter(
            user=user, tenant_id=user.tenant_id, is_active=True,
        ).values_list("role", flat=True)
    )
    current = normalize_role(user.role)
    if current and current not in roles:
        roles.append(current)
    seen: set[str] = set()
    out: list[str] = []
    for r in roles:
        nr = normalize_role(r)
        if nr and nr not in seen and nr != UserRole.SUPER_ADMIN:
            seen.add(nr)
            out.append(nr)
    return out


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
        return user.staff_profile
    except Exception:
        return None


def _safe_parent(user: User):
    try:
        return user.parent_profile
    except Exception:
        return None


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
    """Create minimal Parent/Teacher linkage when dual-granting those portals."""
    role = normalize_role(role)
    actor_ok = actor if getattr(actor, "is_authenticated", False) else None

    if role == UserRole.PARENT:
        from apps.students.models import Parent

        parent = _safe_parent(user)
        if parent is None:
            # Prefer matching by email within tenant
            parent = Parent.objects.filter(
                tenant_id=user.tenant_id, email__iexact=user.email, is_deleted=False,
            ).first()
            if parent and parent.user_id is None:
                parent.user = user
                parent.has_portal_access = True
                parent.save(update_fields=["user", "has_portal_access", "updated_at"])
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
            if parent.user_id is None:
                parent.user = user
            parent.has_portal_access = True
            parent.save(update_fields=["user", "has_portal_access", "updated_at"])
        return

    # Staff / teaching roles — ensure Staff + Teacher where needed
    if role in UserRole.STAFF_ROLES or role == UserRole.SCHOOL_ADMIN:
        from apps.staff.models import Staff, Teacher
        from apps.staff.staff_roles import get_role_definition, role_requires_teacher_profile

        staff = _safe_staff(user)
        if staff is None:
            staff = Staff.objects.filter(
                tenant_id=user.tenant_id, email__iexact=user.email, is_deleted=False,
            ).first()
            if staff and staff.user_id is None:
                staff.user = user
                staff.has_portal_access = True
                if role in dict(UserRole.CHOICES):
                    staff.portal_role = role
                staff.save(update_fields=["user", "has_portal_access", "portal_role", "updated_at"])
            elif staff is None:
                role_def = get_role_definition(role) if role != UserRole.SCHOOL_ADMIN else {
                    "category": "management",
                    "default_designation": "School Administrator",
                }
                # employee_id unique per tenant
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
            if staff.portal_role != role and role != UserRole.PARENT:
                staff.portal_role = role
                staff.save(update_fields=["portal_role", "updated_at"])

        if role_requires_teacher_profile(role) or role in {
            UserRole.TEACHER, UserRole.CLASS_TEACHER, UserRole.HEAD_OF_DEPARTMENT,
            UserRole.DIRECTOR_OF_STUDIES,
        }:
            if not Teacher.objects.filter(staff=staff).exists():
                Teacher.objects.create(
                    tenant_id=user.tenant_id,
                    staff=staff,
                    created_by=actor_ok,
                    updated_by=actor_ok,
                )


@transaction.atomic
def revoke_role(*, user: User, role: str, actor=None) -> dict[str, Any]:
    role = normalize_role(role)
    if not role:
        raise DualRoleError("Role is required.", code="role_required")
    qs = UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, role=role, is_active=True,
    )
    if not qs.exists():
        raise DualRoleError("That role is not assigned.", code="not_assigned")
    remaining = list_user_roles(user)
    if len(remaining) <= 1:
        raise DualRoleError("Cannot remove the only role on this account.", code="last_role")
    qs.update(is_active=False, updated_at=timezone.now())
    if normalize_role(user.role) == role:
        primary = (
            UserRoleAssignment.objects.filter(
                user=user, tenant_id=user.tenant_id, is_active=True, is_primary=True,
            ).first()
            or UserRoleAssignment.objects.filter(
                user=user, tenant_id=user.tenant_id, is_active=True,
            ).first()
        )
        if primary:
            switch_role(user=user, role=primary.role, actor=actor)
    return {
        "user_id": str(user.id),
        "revoked": role,
        "available_roles": list_user_roles(user),
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
