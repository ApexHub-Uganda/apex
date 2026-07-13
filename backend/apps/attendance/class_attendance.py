"""Daily class attendance marking for teachers — class/stream scoped, checkbox-friendly bulk save."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.academics.models import Class, Stream
from apps.academics.scoping import (
    filter_queryset_for_user,
    get_academic_context,
    user_can_access_class,
    user_has_school_wide_academic_access,
)
from apps.attendance.models import AttendanceRecord
from apps.examinations.reference import _option
from apps.students.models import Student


class ClassAttendanceError(Exception):
    def __init__(self, message: str, *, code: str = "class_attendance_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _parse_time(value) -> time | None:
    if not value:
        return None
    if isinstance(value, time):
        return value
    raw = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def class_attendance_scope_meta(user) -> dict:
    ctx = get_academic_context(user)
    return {
        "is_teacher_scoped": not user_has_school_wide_academic_access(user),
        "is_class_teacher": bool(ctx and ctx.is_class_teacher),
    }


def teacher_class_options(tenant, user) -> list[dict]:
    qs = Class.objects.filter(tenant=tenant, is_deleted=False).select_related("academic_year")
    qs = filter_queryset_for_user(qs, user).order_by("name")

    ctx = get_academic_context(user)
    class_teacher_ids = set(ctx.class_teacher_class_ids) if ctx else set()

    rows = []
    for school_class in qs:
        stream_count = Stream.objects.filter(
            tenant=tenant,
            school_class_id=school_class.id,
            is_deleted=False,
        ).count()
        student_count = Student.objects.filter(
            tenant=tenant,
            school_class_id=school_class.id,
            status="active",
            is_deleted=False,
        ).count()
        rows.append({
            **_option(school_class.id, f"{school_class.name} ({school_class.code})"),
            "code": school_class.code,
            "stream_count": stream_count,
            "student_count": student_count,
            "has_streams": stream_count > 0,
            "is_class_teacher": school_class.id in class_teacher_ids,
        })
    return rows


def stream_options_for_class(tenant, *, school_class_id, user) -> list[dict]:
    if not user_can_access_class(user, school_class_id):
        raise ClassAttendanceError("You do not have access to this class.", code="forbidden")

    streams = Stream.objects.filter(
        tenant=tenant,
        school_class_id=school_class_id,
        is_deleted=False,
    ).order_by("name")

    rows = []
    for stream in streams:
        student_count = Student.objects.filter(
            tenant=tenant,
            school_class_id=school_class_id,
            stream_id=stream.id,
            status="active",
            is_deleted=False,
        ).count()
        rows.append({
            **_option(stream.id, stream.name),
            "student_count": student_count,
        })

    unassigned_count = Student.objects.filter(
        tenant=tenant,
        school_class_id=school_class_id,
        stream__isnull=True,
        status="active",
        is_deleted=False,
    ).count()
    if unassigned_count:
        rows.append({
            "value": "unassigned",
            "label": "No stream assigned",
            "student_count": unassigned_count,
        })

    return rows


def students_for_class_marking(
    tenant,
    *,
    school_class_id,
    stream_id=None,
) -> list[Student]:
    students = Student.objects.filter(
        tenant=tenant,
        school_class_id=school_class_id,
        status="active",
        is_deleted=False,
    ).select_related("stream").order_by("last_name", "first_name")

    if stream_id:
        if str(stream_id) == "unassigned":
            students = students.filter(stream__isnull=True)
        else:
            students = students.filter(stream_id=stream_id)
    return list(students)


def existing_attendance_map(tenant, *, students, mark_date: date) -> dict[str, dict]:
    if not students:
        return {}
    student_ids = [s.id for s in students]
    rows = AttendanceRecord.objects.filter(
        tenant=tenant,
        attendee_type="student",
        student_id__in=student_ids,
        date=mark_date,
        is_deleted=False,
    )
    return {
        str(row.student_id): {
            "id": str(row.id),
            "status": row.status,
            "check_in": row.check_in.isoformat() if row.check_in else None,
            "remarks": row.remarks,
        }
        for row in rows
    }


def class_attendance_options_payload(
    tenant,
    user,
    *,
    school_class_id=None,
    stream_id=None,
    mark_date=None,
) -> dict[str, Any]:
    now = timezone.localtime()
    resolved_date = _parse_date(mark_date) or now.date()
    defaults = {
        "date": resolved_date.isoformat(),
        "check_in": now.time().replace(microsecond=0).isoformat(),
    }

    data: dict[str, Any] = {
        "scope_meta": class_attendance_scope_meta(user),
        "classes": teacher_class_options(tenant, user),
        "streams": [],
        "requires_stream": False,
        "students": [],
        "attendance": {},
        "defaults": defaults,
        "selected_class": None,
        "selected_stream": None,
    }

    if not school_class_id:
        return data

    if not user_can_access_class(user, school_class_id):
        raise ClassAttendanceError("You do not have access to this class.", code="forbidden")

    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if school_class is None:
        raise ClassAttendanceError("Class not found.", code="not_found")

    streams = stream_options_for_class(tenant, school_class_id=school_class_id, user=user)
    data["streams"] = streams
    data["requires_stream"] = len(streams) > 0
    data["selected_class"] = _option(school_class.id, school_class.name, code=school_class.code)

    if data["requires_stream"] and not stream_id:
        return data

    if stream_id and not data["requires_stream"]:
        stream_id = None

    if stream_id:
        data["selected_stream"] = next(
            (row for row in streams if str(row["value"]) == str(stream_id)),
            {"value": str(stream_id), "label": "Stream"},
        )

    students = students_for_class_marking(
        tenant,
        school_class_id=school_class_id,
        stream_id=stream_id,
    )
    from apps.students.serializers import StudentListSerializer

    data["students"] = StudentListSerializer(students, many=True).data
    data["attendance"] = existing_attendance_map(tenant, students=students, mark_date=resolved_date)
    return data


@transaction.atomic
def bulk_save_class_attendance(
    *,
    tenant,
    user,
    school_class_id,
    stream_id=None,
    mark_date,
    check_in=None,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    if not user_can_access_class(user, school_class_id):
        raise ClassAttendanceError("You do not have access to this class.", code="forbidden")

    resolved_date = _parse_date(mark_date)
    if resolved_date is None:
        raise ClassAttendanceError("A valid date is required.", code="invalid_date")

    resolved_check_in = _parse_time(check_in)
    if resolved_check_in is None:
        resolved_check_in = timezone.localtime().time().replace(microsecond=0)

    students = students_for_class_marking(
        tenant,
        school_class_id=school_class_id,
        stream_id=stream_id,
    )
    allowed_ids = {str(s.id) for s in students}

    saved = 0
    for row in entries:
        student_id = row.get("student")
        if not student_id or str(student_id) not in allowed_ids:
            continue

        present = row.get("present")
        if present is None:
            present = row.get("status", "present") in ("present", "late", "excused", "half_day")

        status = "present" if present else "absent"
        record_check_in = resolved_check_in if present else None

        record = AttendanceRecord.objects.filter(
            tenant=tenant,
            attendee_type="student",
            student_id=student_id,
            date=resolved_date,
            is_deleted=False,
        ).first()
        if record is None:
            AttendanceRecord.objects.create(
                tenant=tenant,
                attendee_type="student",
                student_id=student_id,
                date=resolved_date,
                status=status,
                check_in=record_check_in,
                remarks=(row.get("remarks") or "").strip(),
                marked_by=user,
                created_by=user,
                updated_by=user,
            )
        else:
            record.status = status
            record.check_in = record_check_in
            record.remarks = (row.get("remarks") or "").strip()
            record.marked_by = user
            record.updated_by = user
            record.save(update_fields=[
                "status", "check_in", "remarks", "marked_by", "updated_by", "updated_at",
            ])
        saved += 1

    return {
        "saved": saved,
        "date": resolved_date.isoformat(),
        "check_in": resolved_check_in.isoformat() if resolved_check_in else None,
    }