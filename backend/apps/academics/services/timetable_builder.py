"""
Class-by-class timetable grid builder.

Periods are school-wide (same from/to every day Mon–Sun). Creators fill a
day × period matrix per class; teaching assignments auto-wire teachers.
Real-time constraint validation checks teacher clashes across classes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError  # noqa: F401 — PermissionDenied used by publish helpers

from apps.academics.models import (
    Class,
    Period,
    Stream,
    Subject,
    TeachingAssignment,
    Term,
    Timetable,
    TimetableSchedule,
)
from apps.academics.singleton import get_active_academic_year, get_active_term
from apps.academics.timetable_generator import assert_timetable_write, DAY_LABELS
from apps.staff.models import Teacher
from apps.tenants.role_permissions import user_is_school_admin

DEFAULT_WORKING_DAYS = [0, 1, 2, 3, 4, 5, 6]  # Mon–Sun available; empty cells allowed


def _parse_time(value) -> time:
    """Accept HH:MM, HH:MM:SS, or datetime.time — same as Period CRUD."""
    if value is None or value == "":
        raise ValidationError("Start and end times are required for every period.")
    if isinstance(value, time):
        return value
    s = str(value).strip()
    # HTML time inputs may send "8:00" or "08:00:00"
    for fmt in ("%H:%M:%S", "%H:%M", "%H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:12], fmt).time()
        except ValueError:
            continue
    raise ValidationError(f'Invalid time "{value}". Use HH:MM (e.g. 08:00).')


def _teacher_name(teacher) -> str:
    if not teacher:
        return ""
    staff = getattr(teacher, "staff", None)
    return staff.full_name if staff else ""


def bulk_sync_periods(*, tenant, user, periods_payload: list[dict]) -> list[Period]:
    """
    Create/update school-wide periods from the timetable wizard.

    Matches the simple Periods page: name, from, to, order, break flag.
    Only hard rule beyond required fields: times must not overlap
    (touching end==next start is allowed).
    """
    assert_timetable_write(user)
    if not periods_payload:
        raise ValidationError("Add at least one period with from and to times.")

    cleaned = []
    for i, raw in enumerate(periods_payload):
        if not isinstance(raw, dict):
            raise ValidationError(f"Period #{i + 1} is invalid.")
        # Auto-name like the periods page defaults if left blank
        name = (raw.get("name") or "").strip() or f"Period {i + 1}"
        try:
            start = _parse_time(raw.get("start_time"))
            end = _parse_time(raw.get("end_time"))
        except ValidationError as exc:
            detail = exc.detail
            msg = detail if isinstance(detail, str) else str(detail)
            raise ValidationError(f'{name}: {msg}') from exc
        if end <= start:
            raise ValidationError(f'"{name}": end time must be after start time.')
        try:
            sort_order = int(raw.get("sort_order") if raw.get("sort_order") not in (None, "") else (i + 1))
        except (TypeError, ValueError):
            sort_order = i + 1
        cleaned.append({
            "id": raw.get("id") or None,
            "name": name[:50],
            "start_time": start,
            "end_time": end,
            "sort_order": sort_order,
            "is_break": bool(raw.get("is_break")),
        })

    # Only constraint: no overlapping times (adjacent OK)
    ordered = sorted(cleaned, key=lambda p: (p["start_time"], p["sort_order"], p["name"]))
    for a, b in zip(ordered, ordered[1:]):
        if b["start_time"] < a["end_time"]:
            raise ValidationError(
                f'"{a["name"]}" ({a["start_time"].strftime("%H:%M")}–{a["end_time"].strftime("%H:%M")}) '
                f'overlaps "{b["name"]}" ({b["start_time"].strftime("%H:%M")}–{b["end_time"].strftime("%H:%M")}). '
                f"Adjust the times so they do not overlap."
            )

    # Ensure unique names within this save (auto-suffix if user duplicates)
    seen_names: dict[str, int] = {}
    for row in cleaned:
        key = row["name"].lower()
        if key in seen_names:
            seen_names[key] += 1
            row["name"] = f"{row['name']} ({seen_names[key]})"
        else:
            seen_names[key] = 1

    keep_ids = []
    result = []
    with transaction.atomic():
        for row in cleaned:
            obj = None
            if row["id"]:
                obj = Period.objects.filter(tenant=tenant, pk=row["id"]).first()
            # Reuse soft-deleted row with same name to avoid unique (tenant, name) clash
            if obj is None:
                obj = Period.objects.filter(
                    tenant=tenant, name__iexact=row["name"],
                ).order_by("is_deleted").first()
            if obj is None:
                obj = Period(tenant=tenant, created_by=user)
            obj.name = row["name"]
            obj.start_time = row["start_time"]
            obj.end_time = row["end_time"]
            obj.sort_order = row["sort_order"]
            obj.is_break = row["is_break"]
            obj.is_deleted = False
            obj.updated_by = user
            obj.save()
            keep_ids.append(obj.id)
            result.append(obj)

        # Soft-delete periods removed from the list
        Period.objects.filter(tenant=tenant, is_deleted=False).exclude(pk__in=keep_ids).update(
            is_deleted=True, updated_by=user, updated_at=timezone.now(),
        )
    return result


def serialize_period(p: Period) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "name": p.name,
        "start_time": p.start_time.strftime("%H:%M"),
        "end_time": p.end_time.strftime("%H:%M"),
        "sort_order": p.sort_order,
        "is_break": p.is_break,
    }


def build_wizard_context(*, tenant, user) -> dict[str, Any]:
    """Full context for the class-by-class timetable wizard."""
    year = get_active_academic_year(tenant)
    term = get_active_term(tenant)
    periods = list(
        Period.objects.filter(tenant=tenant, is_deleted=False).order_by("sort_order", "start_time"),
    )

    from apps.academics.scoping import get_academic_context, user_has_school_wide_academic_access

    classes = Class.objects.filter(tenant=tenant, is_deleted=False)
    if year:
        classes = classes.filter(academic_year=year)
    # Teachers only manage classes they teach (admins / DoS see all)
    if not user_is_school_admin(user) and not user_has_school_wide_academic_access(user):
        ctx = get_academic_context(user)
        if ctx and (ctx.assigned_class_ids or ctx.class_teacher_class_ids):
            allowed = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
            classes = classes.filter(pk__in=allowed)
        elif ctx and ctx.teacher is None:
            classes = classes.none()
    classes = classes.prefetch_related("streams").order_by("name")

    teaching = TeachingAssignment.objects.filter(
        tenant=tenant, is_deleted=False, is_active=True,
    ).select_related("teacher__staff", "school_class", "subject", "academic_year")
    if year:
        teaching = teaching.filter(academic_year=year)

    # Subject catalog for pickers
    from apps.academics.models import Subject
    subjects = Subject.objects.filter(tenant=tenant, is_deleted=False).order_by("name")
    teachers = Teacher.objects.filter(tenant=tenant, is_deleted=False).select_related("staff").order_by(
        "staff__last_name", "staff__first_name",
    )

    assignment_by_class: dict[str, list] = defaultdict(list)
    teacher_for_pair: dict[str, dict] = {}  # f"{class_id}:{subject_id}" -> teacher info
    for row in teaching:
        cid = str(row.school_class_id)
        assignment_by_class[cid].append({
            "id": str(row.id),
            "subject_id": str(row.subject_id),
            "subject_name": row.subject.name if row.subject_id else "",
            "subject_code": row.subject.code if row.subject_id else "",
            "teacher_id": str(row.teacher_id) if row.teacher_id else None,
            "teacher_name": _teacher_name(row.teacher) if row.teacher_id else "",
        })
        if row.subject_id and row.teacher_id:
            teacher_for_pair[f"{cid}:{row.subject_id}"] = {
                "teacher_id": str(row.teacher_id),
                "teacher_name": _teacher_name(row.teacher),
            }

    # Coverage: which classes already have lesson slots this term
    coverage = {}
    if term:
        for cid in Class.objects.filter(tenant=tenant, is_deleted=False).values_list("id", flat=True):
            n = Timetable.objects.filter(
                tenant=tenant, school_class_id=cid, term=term, is_deleted=False,
                schedule_type=TimetableSchedule.SCHEDULE_LESSON,
            ).exclude(is_break_slot=True).count()
            coverage[str(cid)] = n

    class_rows = []
    for c in classes:
        streams = list(c.streams.filter(is_deleted=False).values("id", "name"))
        class_rows.append({
            "id": str(c.id),
            "name": c.name,
            "code": c.code,
            "room": c.room or "",
            "streams": [{"id": str(s["id"]), "name": s["name"]} for s in streams],
            "assignment_count": len(assignment_by_class.get(str(c.id), [])),
            "filled_slots": coverage.get(str(c.id), 0),
            "has_timetable": coverage.get(str(c.id), 0) > 0,
        })

    from apps.academics.scoping import get_teacher_for_user

    viewer_teacher = get_teacher_for_user(user)
    return {
        "academic_year": {"id": str(year.id), "name": year.name} if year else None,
        "active_term": (
            {
                "id": str(term.id),
                "name": term.name,
                "start_date": term.start_date.isoformat(),
                "end_date": term.end_date.isoformat(),
            }
            if term
            else None
        ),
        "periods": [serialize_period(p) for p in periods],
        "classes": class_rows,
        "subjects": [
            {"id": str(s.id), "name": s.name, "code": s.code}
            for s in subjects
        ],
        "teachers": [
            {"id": str(t.id), "name": _teacher_name(t)}
            for t in teachers if t.staff_id
        ],
        "assignments_by_class": dict(assignment_by_class),
        "teacher_for_pair": teacher_for_pair,
        "working_days": [{"value": d, "label": DAY_LABELS[d]} for d in range(7)],
        "default_working_days": [0, 1, 2, 3, 4],
        "is_school_admin": user_is_school_admin(user),
        "viewer_teacher_id": str(viewer_teacher.id) if viewer_teacher else None,
        "viewer_teacher_name": _teacher_name(viewer_teacher) if viewer_teacher else "",
        "readiness": {
            "has_periods": len(periods) > 0,
            "has_classes": len(class_rows) > 0,
            "has_active_term": term is not None,
            "can_build": bool(periods and class_rows and term),
        },
    }



def _cell_dict(*, day, period, entry=None, stream=None, school_class=None) -> dict[str, Any]:
    room = (school_class.room if school_class else "") or ""
    if entry:
        subj_name = (
            (getattr(entry, "display_subject", None) or "").strip()
            or (entry.subject.name if entry.subject_id else "")
            or (entry.slot_label if entry.is_break_slot else "")
            or ""
        )
        tch_name = (
            (getattr(entry, "display_teacher", None) or "").strip()
            or (_teacher_name(entry.teacher) if entry.teacher_id else "")
        )
        return {
            "day_of_week": day,
            "day_label": DAY_LABELS[day],
            "period_id": str(period.id),
            "period_name": period.name,
            "start_time": period.start_time.strftime("%H:%M"),
            "end_time": period.end_time.strftime("%H:%M"),
            "stream_id": str(entry.stream_id) if entry.stream_id else (str(stream.id) if stream else None),
            "stream_name": (
                entry.stream.name if entry.stream_id and getattr(entry, "stream", None)
                else (stream.name if stream else "")
            ),
            "is_break": period.is_break or entry.is_break_slot,
            "subject_id": str(entry.subject_id) if entry.subject_id else None,
            "subject_name": subj_name or (period.name if period.is_break else ""),
            "subject_code": entry.subject.code if entry.subject_id else "",
            "teacher_id": str(entry.teacher_id) if entry.teacher_id else None,
            "teacher_name": tch_name,
            "display_subject": subj_name,
            "display_teacher": tch_name,
            "room": entry.room or room,
            "entry_id": str(entry.id),
            "is_empty": not (entry.subject_id or entry.is_break_slot),
        }
    return {
        "day_of_week": day,
        "day_label": DAY_LABELS[day],
        "period_id": str(period.id),
        "period_name": period.name,
        "start_time": period.start_time.strftime("%H:%M"),
        "end_time": period.end_time.strftime("%H:%M"),
        "stream_id": str(stream.id) if stream else None,
        "stream_name": stream.name if stream else "",
        "is_break": period.is_break,
        "subject_id": None,
        "subject_name": period.name if period.is_break else "",
        "subject_code": "",
        "teacher_id": None,
        "teacher_name": "",
        "room": room,
        "entry_id": None,
        "is_empty": not period.is_break,
    }


def get_class_grid(
    *,
    tenant,
    school_class_id: str,
    term_id: str | None = None,
    stream_id: str | None = None,
    working_days: list[int] | None = None,
) -> dict[str, Any]:
    """Day x period grid; multi-stream when whole class has streams."""
    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if not school_class:
        raise ValidationError({"school_class": "Class not found."})
    term = None
    if term_id:
        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
    if term is None:
        term = get_active_term(tenant)
    if term is None:
        raise ValidationError({"term": "Activate an academic term first."})

    class_streams = list(
        Stream.objects.filter(tenant=tenant, school_class=school_class, is_deleted=False).order_by("name"),
    )
    single_stream = None
    if stream_id:
        single_stream = Stream.objects.filter(
            tenant=tenant, pk=stream_id, school_class=school_class, is_deleted=False,
        ).first()
    multi_stream = bool(not stream_id and len(class_streams) > 0)

    periods = list(
        Period.objects.filter(tenant=tenant, is_deleted=False).order_by("sort_order", "start_time"),
    )
    days = working_days if working_days is not None else [0, 1, 2, 3, 4]
    days = sorted({int(d) for d in days if int(d) in DAY_LABELS})

    qs = Timetable.objects.filter(
        tenant=tenant,
        school_class=school_class,
        term=term,
        is_deleted=False,
        schedule_type=TimetableSchedule.SCHEDULE_LESSON,
    ).select_related("subject", "teacher__staff", "period", "stream")

    if multi_stream:
        qs = qs.filter(stream_id__in=[s.id for s in class_streams])
        existing = {}
        for e in qs:
            if e.period_id and e.day_of_week is not None and e.stream_id:
                existing[(e.day_of_week, str(e.period_id), str(e.stream_id))] = e
        cells = []
        for day in days:
            for p in periods:
                for st in class_streams:
                    key = (day, str(p.id), str(st.id))
                    cells.append(_cell_dict(
                        day=day, period=p, entry=existing.get(key), stream=st, school_class=school_class,
                    ))
    else:
        if single_stream:
            qs = qs.filter(stream=single_stream)
        else:
            qs = qs.filter(stream__isnull=True)
        existing_simple = {}
        for e in qs:
            if e.period_id and e.day_of_week is not None:
                existing_simple[(e.day_of_week, str(e.period_id))] = e
        cells = []
        for day in days:
            for p in periods:
                key = (day, str(p.id))
                cells.append(_cell_dict(
                    day=day, period=p, entry=existing_simple.get(key),
                    stream=single_stream, school_class=school_class,
                ))

    year = term.academic_year or get_active_academic_year(tenant)
    assignments = []
    if year:
        for row in TeachingAssignment.objects.filter(
            tenant=tenant, school_class=school_class, academic_year=year,
            is_deleted=False, is_active=True,
        ).select_related("subject", "teacher__staff"):
            assignments.append({
                "subject_id": str(row.subject_id),
                "subject_name": row.subject.name if row.subject_id else "",
                "subject_code": row.subject.code if row.subject_id else "",
                "teacher_id": str(row.teacher_id) if row.teacher_id else None,
                "teacher_name": _teacher_name(row.teacher) if row.teacher_id else "",
            })

    schedule = (
        TimetableSchedule.objects.filter(
            tenant=tenant, term=term, schedule_type=TimetableSchedule.SCHEDULE_LESSON, is_deleted=False,
        )
        .order_by("-created_at")
        .first()
    )

    return {
        "school_class": {
            "id": str(school_class.id),
            "name": school_class.name,
            "code": school_class.code,
            "room": school_class.room or "",
        },
        "stream": {"id": str(single_stream.id), "name": single_stream.name} if single_stream else None,
        "streams": [{"id": str(s.id), "name": s.name} for s in class_streams],
        "multi_stream": multi_stream,
        "term": {"id": str(term.id), "name": term.name},
        "periods": [serialize_period(p) for p in periods],
        "days": [{"value": d, "label": DAY_LABELS[d]} for d in days],
        "cells": cells,
        "assignments": assignments,
        "schedule": {
            "id": str(schedule.id),
            "status": schedule.status,
            "is_published": schedule.is_published,
            "is_locked": schedule.is_locked,
            "name": schedule.name,
            "published_at": schedule.published_at.isoformat() if schedule.published_at else None,
        } if schedule else None,
    }


def validate_grid_cells(
    *,
    tenant,
    school_class_id: str,
    term_id: str,
    cells: list[dict],
    stream_id: str | None = None,
) -> dict[str, Any]:
    """
    Real-time constraint check without saving.
    Returns conflicts (teacher double-booked, invalid subject, etc.).
    """
    conflicts = []
    warnings = []
    teacher_local: dict[tuple[int, str], list] = defaultdict(list)

    # Constraints from PUBLISHED schedules only (not other users' drafts)
    from django.db.models import Q as DJQ
    other = Timetable.objects.filter(
        tenant=tenant,
        is_deleted=False,
        is_break_slot=False,
        teacher__isnull=False,
        schedule__is_deleted=False,
        schedule__status__in=[
            TimetableSchedule.STATUS_PUBLISHED,
            TimetableSchedule.STATUS_ACTIVE,
        ],
    ).filter(
        DJQ(term_id=term_id)
        | DJQ(schedule_type=TimetableSchedule.SCHEDULE_EXAM)
        | DJQ(schedule__term_id=term_id)
    ).select_related(
        "school_class", "teacher__staff", "period", "subject", "schedule",
    )

    other_busy: dict[tuple[str, int, str], dict] = {}
    for e in other:
        if e.day_of_week is None or not e.period_id or not e.teacher_id:
            continue
        # Skip same class only when same schedule_type lesson — still flag other classes
        if str(e.school_class_id) == str(school_class_id) and e.schedule_type == TimetableSchedule.SCHEDULE_LESSON:
            continue
        other_busy[(str(e.teacher_id), e.day_of_week, str(e.period_id))] = {
            "class_name": e.school_class.name if e.school_class_id else "",
            "subject": (
                getattr(e, "display_subject", None)
                or (e.subject.name if e.subject_id else e.slot_label)
            ),
            "teacher_name": _teacher_name(e.teacher),
            "source": "published",
            "schedule": e.schedule.name if e.schedule_id else "",
        }

    for cell in cells:
        subject_id = cell.get("subject_id") or cell.get("subject")
        if subject_id in ("", "null", "undefined", None):
            subject_id = None
        # Subject always wins over break flag
        if (cell.get("is_break") or cell.get("is_break_slot")) and not subject_id:
            continue
        if not subject_id:
            continue
        day = int(cell["day_of_week"])
        period_id = str(cell["period_id"])
        stream_key = str(cell.get("stream_id") or "")
        teacher_id = cell.get("teacher_id")
        if teacher_id:
            teacher_local[(day, period_id, stream_key)].append(cell)
            key = (str(teacher_id), day, period_id)
            if key in other_busy:
                clash = other_busy[key]
                sched_label = clash.get("schedule") or "another published timetable"
                conflicts.append({
                    "type": "teacher_clash",
                    "day_of_week": day,
                    "day_label": DAY_LABELS.get(day, ""),
                    "period_id": period_id,
                    "period_name": cell.get("period_name") or "",
                    "teacher_id": str(teacher_id),
                    "teacher_name": cell.get("teacher_name") or clash["teacher_name"],
                    "source": clash.get("source") or "published",
                    "published_schedule": sched_label,
                    "message": (
                        f"{cell.get('teacher_name') or 'Teacher'} is already teaching "
                        f"{clash['subject']} in {clash['class_name']} at this time "
                        f"(from published schedule “{sched_label}”)."
                    ),
                })

    # Same teacher in two streams at the same day/period is a real clash
    teacher_across_streams: dict[tuple, set] = defaultdict(set)
    for (day, period_id, stream_key), group in teacher_local.items():
        for c in group:
            tid = c.get("teacher_id")
            if tid:
                teacher_across_streams[(day, period_id, str(tid))].add(stream_key)
    for (day, period_id, tid), streams_set in teacher_across_streams.items():
        if len(streams_set) > 1:
            conflicts.append({
                "type": "teacher_multi_stream",
                "day_of_week": day,
                "period_id": period_id,
                "teacher_id": tid,
                "message": (
                    "Same teacher is assigned to more than one stream in this period. "
                    "Change teacher on one stream, or save with override."
                ),
            })

    filled = sum(1 for c in cells if c.get("subject_id") and not c.get("is_break"))
    empty = sum(1 for c in cells if not c.get("is_break") and not c.get("subject_id"))
    return {
        "ok": len(conflicts) == 0,
        "conflicts": conflicts,
        "warnings": warnings,
        "stats": {"filled": filled, "empty_teaching_slots": empty, "total_cells": len(cells)},
    }


def create_draft_schedule(
    *,
    tenant,
    user,
    term_id: str | None = None,
    name: str = "",
) -> TimetableSchedule:
    """Create a brand-new empty draft timetable (does not reuse an existing one)."""
    assert_timetable_write(user)
    term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first() if term_id else get_active_term(tenant)
    if term is None:
        raise ValidationError("Activate or select an academic term first.")
    # Unique-ish default name so library entries are distinguishable
    base = (name or "").strip() or f"{term.name} Timetable"
    existing_names = set(
        TimetableSchedule.objects.filter(
            tenant=tenant, term=term, is_deleted=False,
        ).values_list("name", flat=True)
    )
    final_name = base
    n = 2
    while final_name in existing_names:
        final_name = f"{base} ({n})"
        n += 1
    return TimetableSchedule.objects.create(
        tenant=tenant,
        created_by=user,
        updated_by=user,
        name=final_name,
        schedule_type=TimetableSchedule.SCHEDULE_LESSON,
        academic_year=term.academic_year,
        term=term,
        status=TimetableSchedule.STATUS_DRAFT,
        is_locked=False,
        applied_at=timezone.now(),
        applied_by=user,
        config={"source": "class_grid_builder"},
        stats={"entry_count": 0, "subjects_saved": 0},
    )


@transaction.atomic
def save_class_grid(
    *,
    tenant,
    user,
    school_class_id: str,
    term_id: str | None,
    stream_id: str | None,
    cells: list[dict],
    working_days: list[int] | None = None,
    schedule_name: str = "",
    schedule_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Persist a full class grid onto a specific draft/published schedule."""
    assert_timetable_write(user)

    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if not school_class:
        raise ValidationError({"school_class": "Class not found."})
    term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first() if term_id else get_active_term(tenant)
    if term is None:
        raise ValidationError({"term": "Academic term required."})

    stream = None
    if stream_id:
        stream = Stream.objects.filter(
            tenant=tenant, pk=stream_id, school_class=school_class, is_deleted=False,
        ).first()
    class_streams = list(
        Stream.objects.filter(tenant=tenant, school_class=school_class, is_deleted=False),
    )
    multi_stream = bool(not stream and class_streams)
    # Detect multi from cells if stream_ids present
    if any(c.get("stream_id") for c in cells):
        multi_stream = True

    from apps.tenants.role_permissions import user_is_school_admin

    validation = validate_grid_cells(
        tenant=tenant,
        school_class_id=str(school_class.id),
        term_id=str(term.id),
        cells=cells,
        stream_id=str(stream.id) if stream else None,
    )
    if validation["conflicts"] and not force:
        raise ValidationError({
            "conflicts": validation["conflicts"],
            "detail": "Resolve teacher clashes or save with force=true to override.",
        })

    # Resolve target schedule: explicit id > create new only if none passed and none exists for edit
    schedule = None
    if schedule_id:
        schedule = TimetableSchedule.objects.filter(
            tenant=tenant, pk=schedule_id, is_deleted=False,
        ).first()
        if schedule is None:
            raise ValidationError("Timetable schedule not found. Create a new draft from the library.")
    else:
        # Prefer an open draft for this term owned by this workflow (latest draft only)
        schedule = (
            TimetableSchedule.objects.filter(
                tenant=tenant,
                term=term,
                schedule_type=TimetableSchedule.SCHEDULE_LESSON,
                status=TimetableSchedule.STATUS_DRAFT,
                is_deleted=False,
            )
            .order_by("-updated_at")
            .first()
        )

    if schedule and schedule.is_published and not user_is_school_admin(user):
        raise ValidationError(
            "This timetable is published. Only a school admin can edit it. "
            "Ask admin to unpublish, or create a new draft."
        )
    if schedule is None:
        schedule = create_draft_schedule(
            tenant=tenant,
            user=user,
            term_id=str(term.id),
            name=schedule_name or f"{term.name} Timetable",
        )
    else:
        if schedule_name and schedule_name.strip() and schedule.status == TimetableSchedule.STATUS_DRAFT:
            schedule.name = schedule_name.strip()[:255]
        if schedule.status not in (TimetableSchedule.STATUS_PUBLISHED, TimetableSchedule.STATUS_ACTIVE):
            schedule.status = TimetableSchedule.STATUS_DRAFT
            schedule.is_locked = False
        schedule.updated_by = user
        schedule.save(update_fields=["name", "status", "is_locked", "updated_by", "updated_at"]
                      if schedule_name else ["status", "is_locked", "updated_by", "updated_at"])

    # Soft-delete existing entries for THIS schedule + class only (never wipe other drafts)
    old_qs = Timetable.objects.filter(
        tenant=tenant,
        schedule=schedule,
        school_class=school_class,
        is_deleted=False,
        schedule_type=TimetableSchedule.SCHEDULE_LESSON,
    )
    if stream and not multi_stream:
        old_qs = old_qs.filter(stream=stream)
    old_qs.update(is_deleted=True, updated_by=user, updated_at=timezone.now())

    period_list = list(Period.objects.filter(tenant=tenant, is_deleted=False))
    periods_by_id = {str(p.id): p for p in period_list}
    # Fallback match by time window (if client still holds an old period id after re-save)
    periods_by_time = {
        (p.start_time.strftime("%H:%M"), p.end_time.strftime("%H:%M")): p
        for p in period_list
    }

    def _resolve_period(cell: dict) -> Period | None:
        pid = str(cell.get("period_id") or "").strip()
        if pid and pid in periods_by_id:
            return periods_by_id[pid]
        st = (cell.get("start_time") or "")[:5]
        et = (cell.get("end_time") or "")[:5]
        if st and et and (st, et) in periods_by_time:
            return periods_by_time[(st, et)]
        return None

    created = 0
    created_teaching = 0
    created_breaks = 0
    skipped_no_period = 0
    skipped_empty = 0
    received_with_subject = sum(
        1 for c in cells
        if c.get("subject_id") not in (None, "", "null", "undefined")
    )

    for cell in cells:
        period = _resolve_period(cell)
        if not period:
            skipped_no_period += 1
            continue
        day = int(cell["day_of_week"])
        subject_id = cell.get("subject_id") or cell.get("subject") or None
        if subject_id in ("", "null", "undefined"):
            subject_id = None
        if subject_id is not None:
            subject_id = str(subject_id)
        teacher_id = cell.get("teacher_id") or cell.get("teacher") or None
        if teacher_id in ("", "null", "undefined"):
            teacher_id = None
        if teacher_id is not None:
            teacher_id = str(teacher_id)

        # CRITICAL: a cell with a subject is NEVER a break — ignore stale is_break flags
        is_break = bool(
            (period.is_break or cell.get("is_break") or cell.get("is_break_slot"))
            and not subject_id
        )

        # Per-cell stream (multi-stream whole-class grid) or scoped stream
        cell_stream = stream
        cell_stream_id = cell.get("stream_id") or None
        if cell_stream_id in ("", "null", "undefined"):
            cell_stream_id = None
        if cell_stream_id:
            cell_stream = Stream.objects.filter(
                tenant=tenant, pk=cell_stream_id, school_class=school_class, is_deleted=False,
            ).first()

        if is_break:
            Timetable.objects.create(
                tenant=tenant,
                created_by=user,
                updated_by=user,
                schedule=schedule,
                school_class=school_class,
                stream=cell_stream,
                subject=None,
                teacher=None,
                period=period,
                term=term,
                schedule_type=TimetableSchedule.SCHEDULE_LESSON,
                day_of_week=day,
                start_time=period.start_time,
                end_time=period.end_time,
                room=cell.get("room") or school_class.room or "",
                is_break_slot=True,
                slot_label=(cell.get("slot_label") or cell.get("subject_name") or period.name or "Break")[:80],
                display_subject="",
                display_teacher="",
            )
            created += 1
            created_breaks += 1
            continue

        if not subject_id:
            skipped_empty += 1
            continue

        subject_obj = Subject.objects.filter(tenant=tenant, pk=subject_id, is_deleted=False).first()
        if subject_obj is None:
            raise ValidationError(
                f"Subject id {subject_id} is not valid for this school. "
                "Re-select the subject on the grid and save again."
            )

        teacher_obj = None
        if teacher_id:
            teacher_obj = Teacher.objects.filter(tenant=tenant, pk=teacher_id, is_deleted=False).first()
        if teacher_obj is None:
            year = term.academic_year or get_active_academic_year(tenant)
            ta = TeachingAssignment.objects.filter(
                tenant=tenant,
                school_class=school_class,
                subject_id=subject_id,
                is_deleted=False,
                is_active=True,
            )
            if year:
                ta = ta.filter(academic_year=year)
            ta = ta.select_related("teacher__staff").first()
            if ta and ta.teacher_id:
                teacher_obj = ta.teacher

        display_subject = (
            (cell.get("subject_name") or cell.get("display_subject") or "").strip()
            or subject_obj.name
            or subject_obj.code
            or ""
        )[:120]
        display_teacher = (
            (cell.get("teacher_name") or cell.get("display_teacher") or "").strip()
            or _teacher_name(teacher_obj)
            or ""
        )[:120]

        Timetable.objects.create(
            tenant=tenant,
            created_by=user,
            updated_by=user,
            schedule=schedule,
            school_class=school_class,
            stream=cell_stream,
            subject=subject_obj,
            teacher=teacher_obj,
            period=period,
            term=term,
            schedule_type=TimetableSchedule.SCHEDULE_LESSON,
            day_of_week=day,
            start_time=period.start_time,
            end_time=period.end_time,
            room=cell.get("room") or school_class.room or "",
            is_break_slot=False,
            slot_label="",
            display_subject=display_subject,
            display_teacher=display_teacher,
        )
        created += 1
        created_teaching += 1

    # Update schedule stats
    total = Timetable.objects.filter(schedule=schedule, is_deleted=False).count()
    subjects_saved = Timetable.objects.filter(
        schedule=schedule, school_class=school_class, is_deleted=False, is_break_slot=False,
        subject__isnull=False,
    ).count()
    schedule.stats = {
        **(schedule.stats or {}),
        "entry_count": total,
        "last_class_saved": school_class.name,
        "last_saved_at": timezone.now().isoformat(),
        "subjects_saved": subjects_saved,
        "received_with_subject": received_with_subject,
        "created_teaching": created_teaching,
        "created_breaks": created_breaks,
    }
    schedule.updated_by = user
    schedule.save(update_fields=["stats", "updated_by", "updated_at"])

    return {
        "schedule_id": str(schedule.id),
        "schedule_status": schedule.status,
        "is_published": schedule.is_published,
        "school_class_id": str(school_class.id),
        "term_id": str(term.id),
        "stream_id": str(stream.id) if stream else None,
        "multi_stream": multi_stream,
        "entries_created": created,
        "subjects_saved": subjects_saved,
        "created_teaching": created_teaching,
        "created_breaks": created_breaks,
        "cells_received": len(cells),
        "received_with_subject": received_with_subject,
        "skipped_unknown_period": skipped_no_period,
        "skipped_empty": skipped_empty,
        "validation": validation,
    }


def publish_timetable_schedule(*, tenant, user, term_id=None, schedule_id=None) -> dict[str, Any]:
    """Publish draft timetable → visible to teachers (read + download).

    Accepts lesson or exam schedules when schedule_id is provided.
    Without schedule_id, defaults to the latest lesson draft for the term.
    """
    assert_timetable_write(user)
    schedule = None
    if schedule_id:
        schedule = TimetableSchedule.objects.filter(
            tenant=tenant, pk=schedule_id, is_deleted=False,
        ).first()
        if schedule is None:
            raise ValidationError("Timetable schedule not found.")
        if schedule.schedule_type == TimetableSchedule.SCHEDULE_EXAM:
            from apps.academics.services.exam_timetable import publish_exam_schedule
            return publish_exam_schedule(tenant=tenant, user=user, schedule_id=str(schedule.id))
    else:
        qs = TimetableSchedule.objects.filter(
            tenant=tenant, is_deleted=False, schedule_type=TimetableSchedule.SCHEDULE_LESSON,
        )
        if term_id:
            schedule = qs.filter(term_id=term_id).order_by("-created_at").first()
        else:
            term = get_active_term(tenant)
            schedule = qs.filter(term=term).order_by("-created_at").first() if term else None
    if not schedule:
        raise ValidationError("No timetable schedule to publish. Save a class grid first.")
    entry_count = Timetable.objects.filter(schedule=schedule, is_deleted=False).count()
    if entry_count == 0:
        raise ValidationError("Cannot publish an empty timetable. Fill and save at least one class.")
    schedule.status = TimetableSchedule.STATUS_PUBLISHED
    schedule.is_locked = True
    schedule.published_at = timezone.now()
    schedule.published_by = user
    schedule.updated_by = user
    schedule.save(update_fields=[
        "status", "is_locked", "published_at", "published_by", "updated_by", "updated_at",
    ])
    return {
        "id": str(schedule.id),
        "status": schedule.status,
        "is_published": True,
        "published_at": schedule.published_at.isoformat(),
        "entry_count": entry_count,
        "schedule_type": schedule.schedule_type,
    }


def unpublish_timetable_schedule(*, tenant, user, schedule_id) -> dict[str, Any]:
    """School admin only — return published timetable to draft for editing."""
    from apps.tenants.role_permissions import user_is_school_admin
    if not user_is_school_admin(user):
        raise PermissionDenied("Only a school admin can unpublish a timetable.")
    schedule = TimetableSchedule.objects.filter(
        tenant=tenant, pk=schedule_id, is_deleted=False,
    ).first()
    if not schedule:
        raise ValidationError("Schedule not found.")
    schedule.status = TimetableSchedule.STATUS_DRAFT
    schedule.is_locked = False
    schedule.updated_by = user
    schedule.save(update_fields=["status", "is_locked", "updated_by", "updated_at"])
    return {"id": str(schedule.id), "status": schedule.status, "is_published": False}


def resolve_default_teacher(*, tenant, school_class_id, subject_id, academic_year=None) -> dict | None:
    year = academic_year or get_active_academic_year(tenant)
    qs = TeachingAssignment.objects.filter(
        tenant=tenant,
        school_class_id=school_class_id,
        subject_id=subject_id,
        is_deleted=False,
        is_active=True,
    ).select_related("teacher__staff")
    if year:
        qs = qs.filter(academic_year=year)
    ta = qs.first()
    if not ta or not ta.teacher_id:
        return None
    return {"teacher_id": str(ta.teacher_id), "teacher_name": _teacher_name(ta.teacher)}
