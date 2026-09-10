"""Class-teacher assignment — single source of truth for who heads a class/stream.

Enterprise rules:
  - Whole-class head: Class.class_teacher
  - Stream head: Stream.class_teacher (optional; classes with streams)
  - Teacher.is_class_teacher mirrors any active head assignment
  - Portal users get class_teacher dual-role access by default (UserRoleAssignment
    source=class_assignment) so they keep subject-teacher access and can switch role
  - Removing the last head clears the flag and auto dual-role (not admin-granted roles)
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.academics.models import Class, Stream
from apps.audit.models import AuditLog
from apps.core.constants import UserRole, normalize_role
from apps.staff.models import Teacher


class ClassTeacherError(Exception):
    def __init__(self, message: str, *, code: str = "class_teacher_error"):
        self.message = message
        self.code = code
        super().__init__(message)


SOURCE_CLASS_ASSIGNMENT = "class_assignment"


def _teacher_user(teacher: Teacher):
    staff = getattr(teacher, "staff", None)
    if staff is None:
        return None
    return getattr(staff, "user", None)


def teacher_heads_any(*, tenant, teacher: Teacher) -> bool:
    if Class.objects.filter(tenant=tenant, class_teacher=teacher, is_deleted=False).exists():
        return True
    return Stream.objects.filter(tenant=tenant, class_teacher=teacher, is_deleted=False).exists()


def sync_teacher_class_teacher_flag(*, tenant, teacher: Teacher) -> bool:
    """Set Teacher.is_class_teacher from live Class/Stream assignments."""
    headed = teacher_heads_any(tenant=tenant, teacher=teacher)
    if teacher.is_class_teacher != headed:
        teacher.is_class_teacher = headed
        teacher.save(update_fields=["is_class_teacher", "updated_at"])
    return headed


def ensure_class_teacher_dual_role(*, teacher: Teacher, actor=None) -> dict[str, Any]:
    """
    Grant class_teacher dual-role access without forcing a role switch.

    Teacher keeps subject-teacher (or other primary) access; class_teacher tools
    are elevated via assignment context + dual-role switcher.
    """
    user = _teacher_user(teacher)
    if user is None or not user.tenant_id:
        return {"granted": False, "reason": "no_portal_user"}

    from apps.accounts.dual_roles import ensure_primary_assignment
    from apps.accounts.models import UserRoleAssignment

    ensure_primary_assignment(user, actor=actor)
    role = UserRole.CLASS_TEACHER

    existing = UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, role=role,
    ).first()
    if existing is not None:
        if existing.is_active:
            return {"granted": False, "reason": "already_held", "user_id": str(user.id)}
        existing.is_active = True
        existing.is_primary = False
        existing.source = SOURCE_CLASS_ASSIGNMENT
        if actor is not None and getattr(actor, "is_authenticated", False):
            existing.granted_by = actor
        existing.save(update_fields=[
            "is_active", "is_primary", "source", "granted_by", "updated_at",
        ])
        return {"granted": True, "reactivated": True, "user_id": str(user.id)}

    # Do not create dual role if their active/primary role is already class_teacher
    if normalize_role(user.role) == role:
        return {"granted": False, "reason": "already_active_role", "user_id": str(user.id)}

    UserRoleAssignment.objects.create(
        user=user,
        tenant_id=user.tenant_id,
        role=role,
        is_primary=False,
        is_active=True,
        source=SOURCE_CLASS_ASSIGNMENT,
        granted_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    return {"granted": True, "reactivated": False, "user_id": str(user.id)}


def revoke_auto_class_teacher_dual_role(*, teacher: Teacher, actor=None) -> dict[str, Any]:
    """Revoke only dual roles auto-granted from class assignment (not admin dual grants)."""
    user = _teacher_user(teacher)
    if user is None or not user.tenant_id:
        return {"revoked": False, "reason": "no_portal_user"}

    from apps.accounts.models import UserRoleAssignment

    qs = UserRoleAssignment.objects.filter(
        user=user,
        tenant_id=user.tenant_id,
        role=UserRole.CLASS_TEACHER,
        is_active=True,
        source=SOURCE_CLASS_ASSIGNMENT,
    )
    if not qs.exists():
        return {"revoked": False, "reason": "none"}

    # Never leave the user with zero roles
    other_active = UserRoleAssignment.objects.filter(
        user=user, tenant_id=user.tenant_id, is_active=True,
    ).exclude(role=UserRole.CLASS_TEACHER).exists()
    if not other_active and normalize_role(user.role) == UserRole.CLASS_TEACHER:
        return {"revoked": False, "reason": "last_role"}

    # If currently acting as class_teacher, switch away first
    if normalize_role(user.role) == UserRole.CLASS_TEACHER:
        other = (
            UserRoleAssignment.objects.filter(
                user=user, tenant_id=user.tenant_id, is_active=True,
            )
            .exclude(role=UserRole.CLASS_TEACHER)
            .order_by("-is_primary")
            .first()
        )
        if other is not None:
            user.role = other.role
            user.save(update_fields=["role", "updated_at"])

    updated = qs.update(is_active=False)
    return {"revoked": updated > 0, "count": updated}


def _after_assignment_change(*, tenant, teacher: Teacher | None, previous: Teacher | None, actor=None):
    """Sync flags + dual roles for teachers involved in an assignment change."""
    seen: set = set()
    for t in (teacher, previous):
        if t is None or t.id in seen:
            continue
        seen.add(t.id)
        headed = sync_teacher_class_teacher_flag(tenant=tenant, teacher=t)
        if headed:
            ensure_class_teacher_dual_role(teacher=t, actor=actor)
        else:
            revoke_auto_class_teacher_dual_role(teacher=t, actor=actor)


@transaction.atomic
def assign_class_teacher(
    *,
    tenant,
    actor,
    school_class_id,
    teacher_id,
    stream_id=None,
    notes: str = "",
) -> dict[str, Any]:
    """
    Assign a class teacher to a whole class or a single stream.

    One class may have a whole-class head and/or per-stream heads.
    Replacing an existing head transfers the dual-role / flag cleanup to the previous teacher.
    """
    school_class = Class.objects.filter(
        tenant=tenant, pk=school_class_id, is_deleted=False,
    ).prefetch_related("streams").first()
    if school_class is None:
        raise ClassTeacherError("Class not found.", code="class_not_found")

    teacher = Teacher.objects.filter(
        tenant=tenant, pk=teacher_id, is_deleted=False,
        staff__is_deleted=False, staff__status="active",
    ).select_related("staff", "staff__user").first()
    if teacher is None:
        raise ClassTeacherError("Teacher not found or inactive.", code="teacher_not_found")

    stream = None
    previous: Teacher | None = None
    scope = "class"

    if stream_id:
        stream = Stream.objects.filter(
            tenant=tenant, pk=stream_id, school_class=school_class, is_deleted=False,
        ).select_related("class_teacher").first()
        if stream is None:
            raise ClassTeacherError("Stream not found for this class.", code="stream_not_found")
        previous = stream.class_teacher
        stream.class_teacher = teacher
        stream.updated_by = actor
        stream.save(update_fields=["class_teacher", "updated_by", "updated_at"])
        scope = "stream"
    else:
        previous = school_class.class_teacher
        school_class.class_teacher = teacher
        school_class.updated_by = actor
        school_class.save(update_fields=["class_teacher", "updated_by", "updated_at"])

    _after_assignment_change(tenant=tenant, teacher=teacher, previous=previous, actor=actor)

    dual = ensure_class_teacher_dual_role(teacher=teacher, actor=actor)

    AuditLog.objects.create(
        tenant=tenant,
        user=actor if getattr(actor, "is_authenticated", False) else None,
        action="class_teacher_assigned",
        resource_type="Class" if scope == "class" else "Stream",
        resource_id=str(stream.id if stream else school_class.id),
        description=(
            f"Assigned {teacher.staff.full_name} as class teacher for "
            f"{school_class.name}"
            + (f" · {stream.name}" if stream else "")
        ),
        changes={
            "teacher_id": str(teacher.id),
            "school_class_id": str(school_class.id),
            "stream_id": str(stream.id) if stream else None,
            "previous_teacher_id": str(previous.id) if previous else None,
            "notes": notes or "",
            "dual_role": dual,
        },
        status_code=200,
    )

    return {
        "scope": scope,
        "school_class_id": str(school_class.id),
        "school_class_name": school_class.name,
        "stream_id": str(stream.id) if stream else None,
        "stream_name": stream.name if stream else None,
        "teacher_id": str(teacher.id),
        "teacher_name": teacher.staff.full_name if teacher.staff_id else "",
        "previous_teacher_id": str(previous.id) if previous else None,
        "dual_role": dual,
        "is_class_teacher_flag": teacher.is_class_teacher,
    }


@transaction.atomic
def unassign_class_teacher(
    *,
    tenant,
    actor,
    school_class_id,
    stream_id=None,
) -> dict[str, Any]:
    school_class = Class.objects.filter(
        tenant=tenant, pk=school_class_id, is_deleted=False,
    ).first()
    if school_class is None:
        raise ClassTeacherError("Class not found.", code="class_not_found")

    previous: Teacher | None = None
    scope = "class"
    stream = None

    if stream_id:
        stream = Stream.objects.filter(
            tenant=tenant, pk=stream_id, school_class=school_class, is_deleted=False,
        ).first()
        if stream is None:
            raise ClassTeacherError("Stream not found for this class.", code="stream_not_found")
        previous = stream.class_teacher
        if previous is None:
            raise ClassTeacherError("No class teacher assigned to this stream.", code="not_assigned")
        stream.class_teacher = None
        stream.updated_by = actor
        stream.save(update_fields=["class_teacher", "updated_by", "updated_at"])
        scope = "stream"
    else:
        previous = school_class.class_teacher
        if previous is None:
            raise ClassTeacherError("No class teacher assigned to this class.", code="not_assigned")
        school_class.class_teacher = None
        school_class.updated_by = actor
        school_class.save(update_fields=["class_teacher", "updated_by", "updated_at"])

    _after_assignment_change(tenant=tenant, teacher=None, previous=previous, actor=actor)

    AuditLog.objects.create(
        tenant=tenant,
        user=actor if getattr(actor, "is_authenticated", False) else None,
        action="class_teacher_unassigned",
        resource_type="Class" if scope == "class" else "Stream",
        resource_id=str(stream.id if stream else school_class.id),
        description=(
            f"Removed class teacher from {school_class.name}"
            + (f" · {stream.name}" if stream else "")
        ),
        changes={
            "previous_teacher_id": str(previous.id) if previous else None,
            "school_class_id": str(school_class.id),
            "stream_id": str(stream.id) if stream else None,
        },
        status_code=200,
    )

    return {
        "scope": scope,
        "school_class_id": str(school_class.id),
        "stream_id": str(stream.id) if stream else None,
        "previous_teacher_id": str(previous.id) if previous else None,
        "previous_teacher_name": previous.staff.full_name if previous and previous.staff_id else "",
    }


def list_class_teacher_assignments(*, tenant) -> list[dict[str, Any]]:
    """Flatten class + stream heads for admin UI."""
    classes = (
        Class.objects.filter(tenant=tenant, is_deleted=False)
        .select_related("class_teacher__staff", "academic_year")
        .prefetch_related(
            # streams with teachers
        )
        .order_by("name")
    )
    streams_by_class: dict = {}
    for st in Stream.objects.filter(tenant=tenant, is_deleted=False).select_related(
        "class_teacher__staff", "school_class",
    ).order_by("name"):
        streams_by_class.setdefault(st.school_class_id, []).append(st)

    rows: list[dict[str, Any]] = []
    for c in classes:
        streams = streams_by_class.get(c.id, [])
        # Whole-class assignment row (always list class; show vacancy if empty)
        rows.append({
            "key": f"class:{c.id}",
            "scope": "class",
            "school_class_id": str(c.id),
            "school_class_name": c.name,
            "school_class_code": c.code or "",
            "academic_year_name": c.academic_year.name if c.academic_year_id else "",
            "stream_id": None,
            "stream_name": None,
            "teacher_id": str(c.class_teacher_id) if c.class_teacher_id else None,
            "teacher_name": (
                c.class_teacher.staff.full_name
                if c.class_teacher_id and c.class_teacher.staff_id
                else None
            ),
            "has_streams": len(streams) > 0,
            "is_assigned": bool(c.class_teacher_id),
            "label": c.name,
        })
        for st in streams:
            rows.append({
                "key": f"stream:{st.id}",
                "scope": "stream",
                "school_class_id": str(c.id),
                "school_class_name": c.name,
                "school_class_code": c.code or "",
                "academic_year_name": c.academic_year.name if c.academic_year_id else "",
                "stream_id": str(st.id),
                "stream_name": st.name,
                "teacher_id": str(st.class_teacher_id) if st.class_teacher_id else None,
                "teacher_name": (
                    st.class_teacher.staff.full_name
                    if st.class_teacher_id and st.class_teacher.staff_id
                    else None
                ),
                "has_streams": True,
                "is_assigned": bool(st.class_teacher_id),
                "label": f"{c.name} · {st.name}",
            })
    return rows


def form_options_class_teachers(*, tenant) -> dict[str, Any]:
    teachers = (
        Teacher.objects.filter(
            tenant=tenant,
            is_deleted=False,
            staff__is_deleted=False,
            staff__status="active",
        )
        .select_related("staff")
        .order_by("staff__first_name", "staff__last_name")
    )
    classes = (
        Class.objects.filter(tenant=tenant, is_deleted=False)
        .select_related("academic_year", "class_teacher__staff")
        .order_by("name")
    )
    streams = (
        Stream.objects.filter(tenant=tenant, is_deleted=False)
        .select_related("school_class", "class_teacher__staff")
        .order_by("school_class__name", "name")
    )
    streams_by_class: dict = {}
    for st in streams:
        streams_by_class.setdefault(str(st.school_class_id), []).append({
            "value": str(st.id),
            "label": st.name,
            "class_teacher_id": str(st.class_teacher_id) if st.class_teacher_id else None,
            "class_teacher_name": (
                st.class_teacher.staff.full_name
                if st.class_teacher_id and st.class_teacher.staff_id
                else None
            ),
        })

    return {
        "teachers": [
            {
                "value": str(t.id),
                "label": t.staff.full_name,
                "designation": t.staff.designation or "",
                "is_class_teacher": bool(t.is_class_teacher),
                "has_portal": bool(getattr(t.staff, "user_id", None) or getattr(t.staff, "has_portal_access", False)),
            }
            for t in teachers
        ],
        "classes": [
            {
                "value": str(c.id),
                "label": f"{c.name} ({c.code})" if c.code else c.name,
                "name": c.name,
                "code": c.code or "",
                "academic_year_name": c.academic_year.name if c.academic_year_id else "",
                "class_teacher_id": str(c.class_teacher_id) if c.class_teacher_id else None,
                "class_teacher_name": (
                    c.class_teacher.staff.full_name
                    if c.class_teacher_id and c.class_teacher.staff_id
                    else None
                ),
                "streams": streams_by_class.get(str(c.id), []),
            }
            for c in classes
        ],
    }


def apply_class_teacher_from_class_update(
    *,
    tenant,
    school_class: Class,
    previous_teacher_id,
    actor=None,
) -> None:
    """Hook when Class.class_teacher is set via ClassSerializer / classes form."""
    prev = None
    if previous_teacher_id:
        prev = Teacher.objects.filter(pk=previous_teacher_id, tenant=tenant).first()
    current = school_class.class_teacher
    if current is not None:
        current = Teacher.objects.filter(pk=current.pk).select_related("staff", "staff__user").first()
    _after_assignment_change(tenant=tenant, teacher=current, previous=prev, actor=actor)
