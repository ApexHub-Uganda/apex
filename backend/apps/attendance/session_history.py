"""Recent attendance sessions history — class day rolls and lesson sessions."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from django.db.models import Count, Q
from django.utils import timezone
from reportlab.platypus import Spacer, Table

from apps.academics.scoping import (
    filter_queryset_for_user,
    user_can_access_class,
    user_has_school_wide_academic_access,
)
from apps.attendance.models import AttendanceRecord, LessonAttendanceEntry, LessonAttendanceSession
from apps.core.pdf_template import branded_table_style, build_branded_pdf, p


class AttendanceSessionHistoryError(Exception):
    def __init__(self, message: str, *, code: str = "attendance_session_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _status_counts_from_statuses(statuses: list[str]) -> dict[str, int]:
    present = 0
    absent = 0
    late = 0
    excused = 0
    other = 0
    for status in statuses:
        s = (status or "present").lower()
        if s == "present":
            present += 1
        elif s == "absent":
            absent += 1
        elif s == "late":
            late += 1
        elif s == "excused":
            excused += 1
        else:
            other += 1
    total = present + absent + late + excused + other
    return {
        "present_count": present,
        "absent_count": absent,
        "late_count": late,
        "excused_count": excused,
        "other_count": other,
        "total_count": total,
        "marked_count": total,
    }


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _scoped_class_ids(user) -> set | None:
    """None = school-wide; else set of class UUIDs the user may see."""
    if user_has_school_wide_academic_access(user):
        return None
    from apps.academics.scoping import get_academic_context

    ctx = get_academic_context(user)
    if ctx is None:
        return set()
    return set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)


def list_recent_attendance_sessions(
    tenant,
    user,
    *,
    limit: int = 40,
    days: int = 60,
) -> list[dict[str, Any]]:
    """
    Recent taken attendance, newest first.

    Includes:
    - lesson sessions (LessonAttendanceSession with entries)
    - daily class rolls (AttendanceRecord student rows grouped by date + class)
    """
    limit = max(1, min(int(limit or 40), 100))
    days = max(1, min(int(days or 60), 180))
    since = timezone.localdate() - timedelta(days=days)
    class_ids = _scoped_class_ids(user)

    sessions: list[dict[str, Any]] = []

    # ── Lesson sessions ────────────────────────────────────────────────────
    lesson_qs = (
        LessonAttendanceSession.objects.filter(
            tenant=tenant,
            is_deleted=False,
            date__gte=since,
        )
        .select_related("school_class", "subject", "teacher", "teacher__staff")
        .annotate(
            present_count=Count(
                "entries",
                filter=Q(entries__is_deleted=False, entries__status="present"),
            ),
            absent_count=Count(
                "entries",
                filter=Q(entries__is_deleted=False, entries__status="absent"),
            ),
            late_count=Count(
                "entries",
                filter=Q(entries__is_deleted=False, entries__status="late"),
            ),
            excused_count=Count(
                "entries",
                filter=Q(entries__is_deleted=False, entries__status="excused"),
            ),
            marked_count=Count("entries", filter=Q(entries__is_deleted=False)),
        )
        .order_by("-date", "-created_at")
    )
    lesson_qs = filter_queryset_for_user(lesson_qs, user)
    for session in lesson_qs[:limit]:
        if session.marked_count == 0:
            continue
        sessions.append({
            "id": f"lesson:{session.id}",
            "session_type": "lesson",
            "source_id": str(session.id),
            "date": session.date.isoformat(),
            "title": session.subject.name if session.subject_id else "Lesson",
            "subtitle": session.school_class.name if session.school_class_id else "",
            "school_class_id": str(session.school_class_id) if session.school_class_id else None,
            "school_class_name": session.school_class.name if session.school_class_id else "",
            "subject_id": str(session.subject_id) if session.subject_id else None,
            "subject_name": session.subject.name if session.subject_id else "",
            "teacher_name": (
                session.teacher.staff.full_name
                if session.teacher_id and session.teacher.staff_id
                else ""
            ),
            "status": session.status,
            "topic": session.topic or "",
            "present_count": session.present_count,
            "absent_count": session.absent_count,
            "late_count": session.late_count,
            "excused_count": session.excused_count,
            "total_count": session.marked_count,
            "marked_count": session.marked_count,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        })

    # ── Daily class rolls (AttendanceRecord) ───────────────────────────────
    student_records = (
        AttendanceRecord.objects.filter(
            tenant=tenant,
            attendee_type="student",
            is_deleted=False,
            date__gte=since,
            student_id__isnull=False,
        )
        .select_related("student", "student__school_class", "marked_by")
        .order_by("-date", "-created_at")
    )
    if class_ids is not None:
        if not class_ids:
            student_records = student_records.none()
        else:
            student_records = student_records.filter(student__school_class_id__in=class_ids)

    # Group by date + class
    groups: dict[tuple[date, Any], dict[str, Any]] = {}
    for row in student_records.iterator(chunk_size=500):
        sc = row.student.school_class if row.student_id else None
        if sc is None:
            continue
        key = (row.date, sc.id)
        if key not in groups:
            groups[key] = {
                "date": row.date,
                "school_class_id": sc.id,
                "school_class_name": sc.name,
                "statuses": [],
                "marked_by_name": "",
                "updated_at": row.updated_at,
            }
        groups[key]["statuses"].append(row.status)
        if row.updated_at and (
            groups[key]["updated_at"] is None or row.updated_at > groups[key]["updated_at"]
        ):
            groups[key]["updated_at"] = row.updated_at
        if row.marked_by_id and not groups[key]["marked_by_name"]:
            user = row.marked_by
            groups[key]["marked_by_name"] = (
                getattr(user, "full_name", None)
                or (user.get_full_name() if hasattr(user, "get_full_name") else "")
                or getattr(user, "email", "")
                or ""
            )

    for (day, class_id), group in groups.items():
        counts = _status_counts_from_statuses(group["statuses"])
        if counts["marked_count"] == 0:
            continue
        sessions.append({
            "id": f"class:{day.isoformat()}:{class_id}",
            "session_type": "class",
            "source_id": f"{day.isoformat()}:{class_id}",
            "date": day.isoformat(),
            "title": "Class attendance",
            "subtitle": group["school_class_name"],
            "school_class_id": str(class_id),
            "school_class_name": group["school_class_name"],
            "subject_id": None,
            "subject_name": "",
            "teacher_name": group["marked_by_name"] or "",
            "status": "recorded",
            "topic": "",
            **counts,
            "created_at": group["updated_at"].isoformat() if group["updated_at"] else None,
        })

    sessions.sort(key=lambda s: (s.get("date") or "", s.get("created_at") or ""), reverse=True)
    return sessions[:limit]


def get_attendance_session_detail(tenant, user, session_key: str) -> dict[str, Any]:
    """
    Detail roster for a session key:
    - lesson:<uuid>
    - class:<YYYY-MM-DD>:<class_uuid>
    """
    raw = (session_key or "").strip()
    if raw.startswith("lesson:"):
        return _lesson_detail(tenant, user, raw[len("lesson:"):])
    if raw.startswith("class:"):
        parts = raw.split(":", 2)
        if len(parts) != 3:
            raise AttendanceSessionHistoryError("Invalid class session id.", code="invalid_id")
        return _class_day_detail(tenant, user, day=parts[1], school_class_id=parts[2])
    # Allow bare lesson UUID for convenience
    try:
        UUID(str(raw))
        return _lesson_detail(tenant, user, raw)
    except (TypeError, ValueError):
        pass
    raise AttendanceSessionHistoryError("Session not found.", code="not_found")


def _lesson_detail(tenant, user, session_id) -> dict[str, Any]:
    qs = LessonAttendanceSession.objects.filter(
        tenant=tenant, pk=session_id, is_deleted=False,
    ).select_related("school_class", "subject", "teacher", "teacher__staff")
    qs = filter_queryset_for_user(qs, user)
    session = qs.first()
    if session is None:
        raise AttendanceSessionHistoryError("Lesson session not found.", code="not_found")

    entries = (
        LessonAttendanceEntry.objects.filter(
            tenant=tenant, session=session, is_deleted=False,
        )
        .select_related("student", "student__stream")
        .order_by("student__last_name", "student__first_name")
    )
    roster = []
    statuses = []
    for entry in entries:
        statuses.append(entry.status)
        roster.append({
            "student_id": str(entry.student_id),
            "admission_number": entry.student.admission_number if entry.student_id else "",
            "full_name": entry.student.full_name if entry.student_id else "",
            "stream_name": entry.student.stream.name if entry.student_id and entry.student.stream_id else "",
            "status": entry.status,
            "remarks": entry.remarks or "",
        })
    counts = _status_counts_from_statuses(statuses)
    return {
        "id": f"lesson:{session.id}",
        "session_type": "lesson",
        "source_id": str(session.id),
        "date": session.date.isoformat(),
        "title": session.subject.name if session.subject_id else "Lesson",
        "subtitle": session.school_class.name if session.school_class_id else "",
        "school_class_id": str(session.school_class_id) if session.school_class_id else None,
        "school_class_name": session.school_class.name if session.school_class_id else "",
        "subject_id": str(session.subject_id) if session.subject_id else None,
        "subject_name": session.subject.name if session.subject_id else "",
        "teacher_name": (
            session.teacher.staff.full_name
            if session.teacher_id and session.teacher.staff_id
            else ""
        ),
        "status": session.status,
        "topic": session.topic or "",
        "notes": session.notes or "",
        **counts,
        "roster": roster,
        "present": [r for r in roster if r["status"] == "present"],
        "absent": [r for r in roster if r["status"] == "absent"],
        "other": [r for r in roster if r["status"] not in ("present", "absent")],
    }


def _class_day_detail(tenant, user, *, day: str, school_class_id) -> dict[str, Any]:
    mark_date = _parse_date(day)
    if mark_date is None:
        raise AttendanceSessionHistoryError("Invalid date.", code="invalid_date")
    if not user_can_access_class(user, school_class_id):
        raise AttendanceSessionHistoryError("You do not have access to this class.", code="forbidden")

    from apps.academics.models import Class

    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if school_class is None:
        raise AttendanceSessionHistoryError("Class not found.", code="not_found")

    records = list(
        AttendanceRecord.objects.filter(
            tenant=tenant,
            attendee_type="student",
            date=mark_date,
            is_deleted=False,
            student__school_class_id=school_class_id,
            student_id__isnull=False,
        )
        .select_related("student", "student__stream", "marked_by")
        .order_by("student__last_name", "student__first_name")
    )
    roster = []
    statuses = []
    marked_by_name = ""
    for rec in records:
        student = rec.student
        if student is None:
            continue
        statuses.append(rec.status)
        if rec.marked_by_id and not marked_by_name:
            user = rec.marked_by
            marked_by_name = (
                getattr(user, "full_name", None)
                or (user.get_full_name() if hasattr(user, "get_full_name") else "")
                or getattr(user, "email", "")
                or ""
            )
        roster.append({
            "student_id": str(student.id),
            "admission_number": student.admission_number,
            "full_name": student.full_name,
            "stream_name": student.stream.name if student.stream_id else "",
            "status": rec.status,
            "remarks": rec.remarks or "",
            "check_in": rec.check_in.isoformat() if rec.check_in else "",
        })
    counts = _status_counts_from_statuses(statuses)
    return {
        "id": f"class:{mark_date.isoformat()}:{school_class_id}",
        "session_type": "class",
        "source_id": f"{mark_date.isoformat()}:{school_class_id}",
        "date": mark_date.isoformat(),
        "title": "Class attendance",
        "subtitle": school_class.name,
        "school_class_id": str(school_class.id),
        "school_class_name": school_class.name,
        "subject_id": None,
        "subject_name": "",
        "teacher_name": marked_by_name,
        "status": "recorded",
        "topic": "",
        "notes": "",
        **counts,
        "roster": roster,
        "present": [r for r in roster if r["status"] == "present"],
        "absent": [r for r in roster if r["status"] == "absent"],
        "other": [r for r in roster if r["status"] not in ("present", "absent")],
    }


def build_attendance_session_pdf(*, tenant, user, session_key: str, request=None) -> bytes:
    detail = get_attendance_session_detail(tenant, user, session_key)

    def story(ctx, styles):
        bits = []
        meta_line = (
            f"{detail.get('school_class_name') or '—'}"
            + (f" · {detail['subject_name']}" if detail.get("subject_name") else "")
            + f" · {detail.get('date') or '—'}"
        )
        if detail.get("teacher_name"):
            meta_line += f" · Taken by {detail['teacher_name']}"
        bits.append(p(meta_line, styles["Meta"]))
        bits.append(Spacer(1, 6))
        bits.append(p(
            f"Present: {detail['present_count']}  ·  Absent: {detail['absent_count']}"
            f"  ·  Late: {detail['late_count']}  ·  Excused: {detail['excused_count']}"
            f"  ·  Total marked: {detail['marked_count']}",
            styles["Body"],
        ))
        bits.append(Spacer(1, 10))

        rows = [[
            p("#", styles["Label"]),
            p("Adm #", styles["Label"]),
            p("Student", styles["Label"]),
            p("Stream", styles["Label"]),
            p("Status", styles["Label"]),
            p("Remarks", styles["Label"]),
        ]]
        for i, row in enumerate(detail.get("roster") or [], start=1):
            rows.append([
                p(str(i), styles["Small"]),
                p(row.get("admission_number") or "—", styles["Small"]),
                p(row.get("full_name") or "—", styles["Small"]),
                p(row.get("stream_name") or "—", styles["Small"]),
                p((row.get("status") or "—").replace("_", " ").title(), styles["Small"]),
                p(row.get("remarks") or "—", styles["Small"]),
            ])
        if len(rows) == 1:
            rows.append([
                p("—", styles["Small"]),
                p("—", styles["Small"]),
                p("No students recorded", styles["Small"]),
                p("—", styles["Small"]),
                p("—", styles["Small"]),
                p("—", styles["Small"]),
            ])
        w = ctx.content_width
        table = Table(
            rows,
            colWidths=[w * 0.06, w * 0.14, w * 0.28, w * 0.14, w * 0.12, w * 0.26],
        )
        table.setStyle(branded_table_style(ctx, header=True))
        bits.append(table)
        bits.append(Spacer(1, 14))
        bits.append(p("Teacher signature: ____________________    Date: ________", styles["Meta"]))
        return bits

    title = "Attendance session"
    if detail.get("session_type") == "lesson":
        title = f"Lesson attendance — {detail.get('subject_name') or 'Lesson'}"
    else:
        title = f"Class attendance — {detail.get('school_class_name') or 'Class'}"

    return build_branded_pdf(
        tenant=tenant,
        document_type="attendance_session",
        document_meta={
            "session": detail.get("id"),
            "date": detail.get("date"),
            "class": detail.get("school_class_name"),
        },
        title=title,
        subtitle=detail.get("date") or "",
        build_story=story,
        request=request,
    )
