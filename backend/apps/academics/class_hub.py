"""Class hub — overview, detail, and prefect management."""
from __future__ import annotations

from typing import Any

from django.db.models import Count, Prefetch, Q

from apps.academics.models import Class, ClassPrefect, Stream
from apps.academics.scoping import get_academic_context, user_has_school_wide_academic_access
from apps.core.constants import UserRole, normalize_role
from apps.students.models import Student
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin


def _resolve_class_id(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "pk"):
        return str(value.pk)
    return str(value)


def user_has_student_enrollment_write(user) -> bool:
    """Write access for enrolling students (full student module or class-teacher tools)."""
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        return False
    return (
        user_can_access_feature(tenant, user, "student_management", require_write=True)
        or user_can_access_feature(tenant, user, "class_teacher_tools", require_write=True)
    )


def user_can_enroll_students(
    user,
    school_class: Class | None = None,
    *,
    school_class_id: str | None = None,
) -> bool:
    """School admins enroll anywhere; class teachers with enrollment write enroll in their classes."""
    if user_is_school_admin(user):
        return True

    if not user_has_student_enrollment_write(user):
        return False

    target_id = _resolve_class_id(school_class) or _resolve_class_id(school_class_id)
    ctx = get_academic_context(user)
    if ctx is None:
        return False

    if target_id:
        if ctx.class_teacher_class_ids and str(target_id) in {str(cid) for cid in ctx.class_teacher_class_ids}:
            return True
        if user_has_school_wide_academic_access(user):
            return True
        return False

    return bool(ctx.class_teacher_class_ids) or user_has_school_wide_academic_access(user)


def user_can_write_classes(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        return False
    if not user_can_access_feature(tenant, user, "classes", require_write=True):
        return False
    return user_has_school_wide_academic_access(user)


def user_can_manage_class_prefects(user, school_class: Class) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    role = normalize_role(getattr(user, "role", ""))
    if role == UserRole.DIRECTOR_OF_STUDIES:
        return True
    if role == UserRole.CLASS_TEACHER:
        ctx = get_academic_context(user)
        return bool(ctx and school_class.id in ctx.class_teacher_class_ids)
    ctx = get_academic_context(user)
    if ctx and ctx.is_class_teacher and school_class.id in ctx.class_teacher_class_ids:
        return True
    return False


def active_student_count(school_class: Class, *, stream_id: str | None = None) -> int:
    qs = school_class.students.filter(is_deleted=False, status="active")
    if stream_id:
        qs = qs.filter(stream_id=stream_id)
    return qs.count()


def build_class_deletion_preview(school_class: Class, *, user) -> dict[str, Any]:
    active_students = active_student_count(school_class)
    stream_count = school_class.streams.filter(is_deleted=False).count()
    prefect_count = school_class.prefects.filter(is_deleted=False).count()
    can_write = user_can_write_classes(user)
    blockers: list[str] = []
    if active_students:
        blockers.append(f"{active_students} active student(s) are still enrolled in this class.")
    if not can_write:
        blockers.append("You do not have permission to delete classes.")
    return {
        "can_delete": can_write and not blockers,
        "active_student_count": active_students,
        "stream_count": stream_count,
        "prefect_count": prefect_count,
        "blockers": blockers,
    }


def build_class_hub_permissions(user, school_class: Class) -> dict[str, bool]:
    can_write_class = user_can_write_classes(user)
    can_manage_prefects = user_can_manage_class_prefects(user, school_class)
    preview = build_class_deletion_preview(school_class, user=user)
    return {
        "can_read": True,
        "can_write_class": can_write_class,
        "can_delete_class": bool(preview["can_delete"]),
        "can_manage_streams": can_write_class,
        "can_manage_prefects": can_manage_prefects,
        "can_enroll_students": user_can_enroll_students(user, school_class),
    }


def soft_delete_class_graph(school_class: Class, *, user) -> None:
    tenant = school_class.tenant
    ClassPrefect.objects.filter(
        tenant=tenant,
        school_class=school_class,
        is_deleted=False,
    ).update(is_deleted=True, updated_by=user)
    Stream.objects.filter(
        tenant=tenant,
        school_class=school_class,
        is_deleted=False,
    ).update(is_deleted=True, updated_by=user)
    school_class.soft_delete(user=user)


def _active_students_qs(tenant):
    return Student.objects.filter(
        tenant=tenant,
        is_deleted=False,
        status="active",
    ).select_related("stream").order_by("last_name", "first_name")


def _stream_student_count(stream: Stream) -> int:
    if hasattr(stream, "_active_student_count"):
        return stream._active_student_count
    return stream.students.filter(is_deleted=False, status="active").count()


def _class_student_count(school_class: Class, *, stream_id: str | None = None) -> int:
    qs = school_class.students.filter(is_deleted=False, status="active")
    if stream_id:
        qs = qs.filter(stream_id=stream_id)
    return qs.count()


def serialize_stream_summary(stream: Stream) -> dict[str, Any]:
    return {
        "id": str(stream.id),
        "name": stream.name,
        "capacity": stream.capacity,
        "student_count": _stream_student_count(stream),
    }


def serialize_class_teacher(school_class: Class) -> dict[str, Any]:
    teacher = school_class.class_teacher
    if not teacher or not teacher.staff:
        return {
            "id": None,
            "name": None,
            "display": "Not assigned",
        }
    name = teacher.staff.full_name
    return {
        "id": str(teacher.id),
        "name": name,
        "display": name,
    }


def serialize_prefect(prefect: ClassPrefect) -> dict[str, Any]:
    student = prefect.student
    return {
        "id": str(prefect.id),
        "student_id": str(student.id),
        "student_name": student.full_name,
        "admission_number": student.admission_number,
        "stream_id": str(prefect.stream_id) if prefect.stream_id else None,
        "stream_name": prefect.stream.name if prefect.stream_id else None,
        "role": prefect.role,
        "role_display": prefect.get_role_display(),
    }


def serialize_student_row(student: Student) -> dict[str, Any]:
    return {
        "id": str(student.id),
        "full_name": student.full_name,
        "admission_number": student.admission_number,
        "gender": student.gender,
        "stream_id": str(student.stream_id) if student.stream_id else None,
        "stream_name": student.stream.name if student.stream_id else None,
    }


def classes_overview_queryset(tenant):
    stream_qs = Stream.objects.filter(
        tenant=tenant,
        is_deleted=False,
    ).annotate(
        _active_student_count=Count(
            "students",
            filter=Q(students__is_deleted=False, students__status="active"),
        ),
    ).order_by("name")

    return Class.objects.filter(
        tenant=tenant,
        is_deleted=False,
    ).select_related(
        "academic_year",
        "class_teacher",
        "class_teacher__staff",
    ).prefetch_related(
        Prefetch("streams", queryset=stream_qs),
    ).annotate(
        _active_student_count=Count(
            "students",
            filter=Q(students__is_deleted=False, students__status="active"),
        ),
    ).order_by("name")


def build_class_overview_row(school_class: Class) -> dict[str, Any]:
    streams = list(school_class.streams.all())
    return {
        "id": str(school_class.id),
        "name": school_class.name,
        "code": school_class.code,
        "academic_year_id": str(school_class.academic_year_id),
        "academic_year_name": school_class.academic_year.name,
        "level_type": school_class.level_type,
        "curriculum": school_class.curriculum,
        "section": school_class.section,
        "capacity": school_class.capacity,
        "room": school_class.room,
        "class_teacher": serialize_class_teacher(school_class),
        "student_count": getattr(school_class, "_active_student_count", _class_student_count(school_class)),
        "stream_count": len(streams),
        "has_streams": len(streams) > 0,
        "streams": [serialize_stream_summary(stream) for stream in streams],
    }


def build_class_hub_detail(
    school_class: Class,
    *,
    tenant,
    user,
    stream_id: str | None = None,
) -> dict[str, Any]:
    streams = list(
        Stream.objects.filter(
            tenant=tenant,
            school_class=school_class,
            is_deleted=False,
        ).annotate(
            _active_student_count=Count(
                "students",
                filter=Q(students__is_deleted=False, students__status="active"),
            ),
        ).order_by("name"),
    )
    selected_stream = None
    if stream_id:
        selected_stream = next((row for row in streams if str(row.id) == str(stream_id)), None)

    prefects_qs = ClassPrefect.objects.filter(
        tenant=tenant,
        school_class=school_class,
        is_deleted=False,
    ).select_related("student", "stream")
    if stream_id:
        prefects_qs = prefects_qs.filter(Q(stream_id=stream_id) | Q(stream__isnull=True))

    students_qs = _active_students_qs(tenant).filter(school_class=school_class)
    if stream_id:
        students_qs = students_qs.filter(stream_id=stream_id)

    scope_label = school_class.name
    if selected_stream:
        scope_label = f"{school_class.name} · {selected_stream.name}"

    return {
        "id": str(school_class.id),
        "name": school_class.name,
        "code": school_class.code,
        "scope_label": scope_label,
        "academic_year_id": str(school_class.academic_year_id),
        "academic_year_name": school_class.academic_year.name,
        "level_type": school_class.level_type,
        "curriculum": school_class.curriculum,
        "section": school_class.section,
        "capacity": school_class.capacity,
        "room": school_class.room or None,
        "room_display": school_class.room or "Not assigned",
        "class_teacher": serialize_class_teacher(school_class),
        "selected_stream_id": str(selected_stream.id) if selected_stream else None,
        "selected_stream_name": selected_stream.name if selected_stream else None,
        "has_streams": len(streams) > 0,
        "streams": [serialize_stream_summary(stream) for stream in streams],
        "prefects": [serialize_prefect(prefect) for prefect in prefects_qs],
        "prefects_display": (
            [serialize_prefect(prefect) for prefect in prefects_qs]
            if prefects_qs.exists()
            else []
        ),
        "students": [serialize_student_row(student) for student in students_qs[:500]],
        "student_count": students_qs.count(),
        "permissions": build_class_hub_permissions(user, school_class),
        "can_manage_prefects": user_can_manage_class_prefects(user, school_class),
        "can_manage_class": user_can_write_classes(user),
        "can_delete_class": build_class_deletion_preview(school_class, user=user)["can_delete"],
        "can_enroll_students": user_can_enroll_students(user, school_class),
    }