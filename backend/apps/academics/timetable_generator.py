"""Constraint-aware lesson and exam timetable generation."""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.academics.models import (
    Class,
    Period,
    Stream,
    TeachingAssignment,
    Term,
    Timetable,
    TimetableGenerationDraft,
    TimetableSchedule,
)
from apps.academics.singleton import get_active_academic_year, get_active_term
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin

DAY_LABELS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

DEFAULT_WORKING_DAYS = [0, 1, 2, 3, 4]
DRAFT_TTL_HOURS = 6


def assert_timetable_write(user) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    if user_is_school_admin(user):
        return
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        raise PermissionDenied("No school context.")
    if not user_can_access_feature(tenant, user, "timetables", require_write=True):
        raise PermissionDenied("You need write access to Timetables to generate schedules.")


def assert_timetable_admin_lock(user) -> None:
    """Mutations against an active/locked schedule require school admin."""
    if not user_is_school_admin(user):
        raise PermissionDenied(
            "This timetable is locked. Only a school admin can edit or delete it for the term/exam session.",
        )


def schedule_is_locked_for_user(schedule: TimetableSchedule | None, user) -> bool:
    if schedule is None:
        return False
    if not schedule.is_locked and schedule.status != TimetableSchedule.STATUS_ACTIVE:
        return False
    return not user_is_school_admin(user)


def build_generation_context(tenant) -> dict[str, Any]:
    """Prerequisites shown before generating."""
    year = get_active_academic_year(tenant)
    term = get_active_term(tenant)
    periods = list(
        Period.objects.filter(tenant=tenant, is_deleted=False).order_by("sort_order", "start_time"),
    )
    teaching = TeachingAssignment.objects.filter(
        tenant=tenant, is_deleted=False, is_active=True,
    ).select_related("teacher__staff", "school_class", "subject", "academic_year")
    if year:
        teaching = teaching.filter(academic_year=year)

    classes = Class.objects.filter(tenant=tenant, is_deleted=False)
    if year:
        classes = classes.filter(academic_year=year)
    classes = classes.prefetch_related("streams").order_by("name")

    class_rows = []
    for school_class in classes:
        streams = list(school_class.streams.filter(is_deleted=False).values("id", "name"))
        class_rows.append({
            "id": str(school_class.id),
            "name": school_class.name,
            "code": school_class.code,
            "streams": [{"id": str(s["id"]), "name": s["name"]} for s in streams],
            "stream_count": len(streams),
        })

    assignment_rows = []
    for row in teaching:
        assignment_rows.append({
            "id": str(row.id),
            "teacher_id": str(row.teacher_id),
            "teacher_name": row.teacher.staff.full_name if row.teacher_id and row.teacher.staff_id else "",
            "school_class_id": str(row.school_class_id),
            "school_class_name": row.school_class.name if row.school_class_id else "",
            "subject_id": str(row.subject_id),
            "subject_name": row.subject.name if row.subject_id else "",
            "subject_code": row.subject.code if row.subject_id else "",
        })

    period_rows = [
        {
            "id": str(p.id),
            "name": p.name,
            "start_time": p.start_time.strftime("%H:%M"),
            "end_time": p.end_time.strftime("%H:%M"),
            "sort_order": p.sort_order,
            "is_break": p.is_break,
        }
        for p in periods
    ]

    from apps.examinations.models import ExaminationSession

    sessions = ExaminationSession.objects.filter(
        tenant=tenant, is_deleted=False,
    ).exclude(status="closed").order_by("-start_date")[:20]
    session_rows = [
        {
            "id": str(s.id),
            "name": s.name,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "status": s.status,
            "term_id": str(s.term_id) if s.term_id else None,
            "academic_year_id": str(s.academic_year_id) if s.academic_year_id else None,
        }
        for s in sessions
    ]

    teaching_periods = [p for p in period_rows if not p["is_break"]]
    readiness = {
        "has_classes": len(class_rows) > 0,
        "has_teaching_periods": len(teaching_periods) > 0,
        "has_teaching_assignments": len(assignment_rows) > 0,
        "has_active_term": term is not None,
        "has_exam_sessions": len(session_rows) > 0,
        "can_generate_lessons": bool(
            class_rows and teaching_periods and assignment_rows and term,
        ),
        "can_generate_exams": bool(
            class_rows and teaching_periods and assignment_rows and session_rows,
        ),
    }

    return {
        "academic_year": (
            {"id": str(year.id), "name": year.name} if year else None
        ),
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
        "classes": class_rows,
        "periods": period_rows,
        "teaching_assignments": assignment_rows,
        "examination_sessions": session_rows,
        "working_days": [
            {"value": d, "label": DAY_LABELS[d]} for d in DEFAULT_WORKING_DAYS
        ],
        "readiness": readiness,
        "defaults": {
            "lessons_per_subject_per_week": 4,
            "working_days": DEFAULT_WORKING_DAYS,
            "use_streams": True,
            "period_ids": [p["id"] for p in teaching_periods],
        },
    }


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    return datetime.strptime(str(value)[:5], "%H:%M").time()


def _load_periods(tenant, period_ids: list[str] | None) -> list[Period]:
    qs = Period.objects.filter(tenant=tenant, is_deleted=False, is_break=False)
    if period_ids:
        qs = qs.filter(id__in=period_ids)
    return list(qs.order_by("sort_order", "start_time"))


def _load_requirements(
    tenant,
    *,
    academic_year,
    class_ids: list[str] | None,
    lessons_per_subject: int,
    use_streams: bool,
) -> list[dict[str, Any]]:
    teaching = TeachingAssignment.objects.filter(
        tenant=tenant, is_deleted=False, is_active=True,
    ).select_related("teacher__staff", "school_class", "subject")
    if academic_year:
        teaching = teaching.filter(academic_year=academic_year)
    if class_ids:
        teaching = teaching.filter(school_class_id__in=class_ids)

    requirements: list[dict[str, Any]] = []
    for row in teaching:
        streams = list(row.school_class.streams.filter(is_deleted=False)) if use_streams else []
        targets = streams or [None]
        for stream in targets:
            for _ in range(max(1, lessons_per_subject)):
                requirements.append({
                    "school_class_id": row.school_class_id,
                    "school_class_name": row.school_class.name,
                    "stream_id": stream.id if stream else None,
                    "stream_name": stream.name if stream else "",
                    "subject_id": row.subject_id,
                    "subject_name": row.subject.name,
                    "subject_code": row.subject.code,
                    "teacher_id": row.teacher_id,
                    "teacher_name": (
                        row.teacher.staff.full_name
                        if row.teacher_id and row.teacher.staff_id
                        else ""
                    ),
                    "room": row.school_class.room or "",
                })
    return requirements


def generate_lesson_slots(
    *,
    tenant,
    working_days: list[int],
    periods: list[Period],
    requirements: list[dict[str, Any]],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rng = random.Random(seed)
    days = sorted(set(working_days)) or DEFAULT_WORKING_DAYS
    if not periods:
        raise ValidationError({"periods": "Add teaching periods (non-break) before generating a timetable."})
    if not requirements:
        raise ValidationError({
            "teaching_assignments": (
                "No teaching assignments found. Assign teachers to classes and subjects first."
            ),
        })

    slots: list[dict[str, Any]] = []
    teacher_busy: set[tuple[int, str, str]] = set()  # day, period_id, teacher
    class_busy: set[tuple[int, str, str, str]] = set()  # day, period, class, stream

    # Flatten available cells and shuffle for variety on regenerate
    cells: list[tuple[int, Period]] = [(d, p) for d in days for p in periods]
    reqs = list(requirements)
    rng.shuffle(reqs)
    rng.shuffle(cells)

    unplaced = 0
    placed_by_subject: dict[str, int] = defaultdict(int)

    for req in reqs:
        placed = False
        # Prefer spreading across days: try cells in shuffled order
        for day, period in cells:
            period_id = str(period.id)
            stream_key = str(req["stream_id"] or "")
            teacher_key = (day, period_id, str(req["teacher_id"]))
            class_key = (day, period_id, str(req["school_class_id"]), stream_key)
            if teacher_key in teacher_busy or class_key in class_busy:
                continue
            teacher_busy.add(teacher_key)
            class_busy.add(class_key)
            slots.append({
                "school_class_id": str(req["school_class_id"]),
                "school_class_name": req["school_class_name"],
                "stream_id": str(req["stream_id"]) if req["stream_id"] else None,
                "stream_name": req["stream_name"],
                "subject_id": str(req["subject_id"]),
                "subject_name": req["subject_name"],
                "subject_code": req["subject_code"],
                "teacher_id": str(req["teacher_id"]) if req["teacher_id"] else None,
                "teacher_name": req["teacher_name"],
                "period_id": period_id,
                "period_name": period.name,
                "day_of_week": day,
                "day_label": DAY_LABELS.get(day, str(day)),
                "start_time": period.start_time.strftime("%H:%M"),
                "end_time": period.end_time.strftime("%H:%M"),
                "room": req["room"],
                "exam_date": None,
            })
            placed_by_subject[req["subject_code"] or req["subject_name"]] += 1
            placed = True
            break
        if not placed:
            unplaced += 1

    warnings: list[str] = []
    if unplaced:
        warnings.append(
            f"{unplaced} lesson request(s) could not be placed without conflicts. "
            "Add more periods, reduce lessons per subject, or hire/assign more teachers.",
        )
    total = len(requirements)
    stats = {
        "requested_slots": total,
        "placed_slots": len(slots),
        "unplaced_slots": unplaced,
        "placement_rate": round((len(slots) / total) * 100, 1) if total else 0,
        "classes": len({s["school_class_id"] for s in slots}),
        "teachers": len({s["teacher_id"] for s in slots if s["teacher_id"]}),
        "subjects": len({s["subject_id"] for s in slots}),
        "days": days,
        "periods_used": len(periods),
        "by_subject": dict(placed_by_subject),
        "seed": seed,
    }
    return slots, stats, warnings


def generate_exam_slots(
    *,
    tenant,
    session,
    periods: list[Period],
    class_ids: list[str] | None,
    seed: int,
    exams_per_day: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rng = random.Random(seed)
    if not periods:
        raise ValidationError({"periods": "Add periods to define exam sitting times."})

    teaching = TeachingAssignment.objects.filter(
        tenant=tenant, is_deleted=False, is_active=True,
    ).select_related("teacher__staff", "school_class", "subject")
    if session.academic_year_id:
        teaching = teaching.filter(academic_year_id=session.academic_year_id)
    if class_ids:
        teaching = teaching.filter(school_class_id__in=class_ids)

    # One exam paper per class-subject (not weekly repeats)
    unique_exams: dict[tuple[str, str], dict[str, Any]] = {}
    for row in teaching:
        key = (str(row.school_class_id), str(row.subject_id))
        if key in unique_exams:
            continue
        unique_exams[key] = {
            "school_class_id": row.school_class_id,
            "school_class_name": row.school_class.name,
            "stream_id": None,
            "stream_name": "",
            "subject_id": row.subject_id,
            "subject_name": row.subject.name,
            "subject_code": row.subject.code,
            "teacher_id": row.teacher_id,
            "teacher_name": (
                row.teacher.staff.full_name
                if row.teacher_id and row.teacher.staff_id
                else ""
            ),
            "room": row.school_class.room or "",
        }

    exams = list(unique_exams.values())
    rng.shuffle(exams)
    if not exams:
        raise ValidationError({
            "teaching_assignments": "No class-subject assignments available to schedule exams.",
        })

    # Calendar days in session range (weekdays only by default)
    days: list[date] = []
    cursor = session.start_date
    while cursor <= session.end_date:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    if not days:
        days = [session.start_date]

    # Use up to exams_per_day teaching periods per day
    sitting_periods = periods[: max(1, exams_per_day)]
    cells: list[tuple[date, Period]] = [(d, p) for d in days for p in sitting_periods]
    rng.shuffle(cells)

    slots: list[dict[str, Any]] = []
    class_busy: set[tuple[str, str, str]] = set()  # date, period, class
    subject_day: set[tuple[str, str]] = set()  # date, subject — same subject not twice same day if avoidable

    unplaced = 0
    for exam in exams:
        placed = False
        preferred = [
            c for c in cells
            if (c[0].isoformat(), str(exam["subject_id"])) not in subject_day
        ] or cells
        for exam_date, period in preferred:
            key = (exam_date.isoformat(), str(period.id), str(exam["school_class_id"]))
            if key in class_busy:
                continue
            class_busy.add(key)
            subject_day.add((exam_date.isoformat(), str(exam["subject_id"])))
            slots.append({
                "school_class_id": str(exam["school_class_id"]),
                "school_class_name": exam["school_class_name"],
                "stream_id": None,
                "stream_name": "",
                "subject_id": str(exam["subject_id"]),
                "subject_name": exam["subject_name"],
                "subject_code": exam["subject_code"],
                "teacher_id": str(exam["teacher_id"]) if exam["teacher_id"] else None,
                "teacher_name": exam["teacher_name"],
                "period_id": str(period.id),
                "period_name": period.name,
                "day_of_week": exam_date.weekday(),
                "day_label": DAY_LABELS.get(exam_date.weekday(), ""),
                "start_time": period.start_time.strftime("%H:%M"),
                "end_time": period.end_time.strftime("%H:%M"),
                "room": exam["room"],
                "exam_date": exam_date.isoformat(),
            })
            placed = True
            break
        if not placed:
            unplaced += 1

    warnings: list[str] = []
    if unplaced:
        warnings.append(
            f"{unplaced} exam(s) could not be placed in the session window. "
            "Extend the examination session dates or add more sittings per day.",
        )
    total = len(exams)
    stats = {
        "requested_slots": total,
        "placed_slots": len(slots),
        "unplaced_slots": unplaced,
        "placement_rate": round((len(slots) / total) * 100, 1) if total else 0,
        "classes": len({s["school_class_id"] for s in slots}),
        "subjects": len({s["subject_id"] for s in slots}),
        "session_days": len(days),
        "sittings_per_day": len(sitting_periods),
        "seed": seed,
    }
    return slots, stats, warnings


def create_generation_draft(
    *,
    tenant,
    user,
    schedule_type: str,
    config: dict[str, Any],
    seed: int | None = None,
) -> TimetableGenerationDraft:
    assert_timetable_write(user)
    schedule_type = (schedule_type or TimetableSchedule.SCHEDULE_LESSON).lower()
    if schedule_type not in (TimetableSchedule.SCHEDULE_LESSON, TimetableSchedule.SCHEDULE_EXAM):
        raise ValidationError({"schedule_type": "Must be 'lesson' or 'exam'."})

    seed = int(seed if seed is not None else timezone.now().timestamp()) % (2**31)
    working_days = config.get("working_days") or DEFAULT_WORKING_DAYS
    working_days = [int(d) for d in working_days if int(d) in DAY_LABELS]
    period_ids = config.get("period_ids") or []
    class_ids = config.get("class_ids") or []
    lessons_per_subject = int(config.get("lessons_per_subject_per_week") or 4)
    use_streams = bool(config.get("use_streams", True))
    exams_per_day = int(config.get("exams_per_day") or 2)

    periods = _load_periods(tenant, period_ids or None)
    year = get_active_academic_year(tenant)
    term = None
    session = None
    name = (config.get("name") or "").strip()

    if schedule_type == TimetableSchedule.SCHEDULE_LESSON:
        term_id = config.get("term_id")
        if term_id:
            term = Term.objects.filter(tenant=tenant, id=term_id, is_deleted=False).first()
        else:
            term = get_active_term(tenant)
        if term is None:
            raise ValidationError({"term_id": "Select or activate an academic term first."})
        if not name:
            name = f"{term.name} Lesson Timetable"
        requirements = _load_requirements(
            tenant,
            academic_year=term.academic_year or year,
            class_ids=class_ids or None,
            lessons_per_subject=lessons_per_subject,
            use_streams=use_streams,
        )
        slots, stats, warnings = generate_lesson_slots(
            tenant=tenant,
            working_days=working_days,
            periods=periods,
            requirements=requirements,
            seed=seed,
        )
        academic_year = term.academic_year
    else:
        from apps.examinations.models import ExaminationSession

        session_id = config.get("examination_session_id")
        if not session_id:
            raise ValidationError({"examination_session_id": "Select an examination session."})
        session = ExaminationSession.objects.filter(
            tenant=tenant, id=session_id, is_deleted=False,
        ).first()
        if session is None:
            raise ValidationError({"examination_session_id": "Examination session not found."})
        if not name:
            name = f"{session.name} Exam Timetable"
        slots, stats, warnings = generate_exam_slots(
            tenant=tenant,
            session=session,
            periods=periods,
            class_ids=class_ids or None,
            seed=seed,
            exams_per_day=exams_per_day,
        )
        academic_year = session.academic_year
        term = session.term

    expires = timezone.now() + timedelta(hours=DRAFT_TTL_HOURS)
    draft = TimetableGenerationDraft.objects.create(
        tenant=tenant,
        created_by=user,
        updated_by=user,
        schedule_type=schedule_type,
        term=term,
        examination_session=session,
        academic_year=academic_year,
        name=name,
        seed=seed,
        config={
            **config,
            "working_days": working_days,
            "period_ids": [str(p.id) for p in periods],
            "class_ids": class_ids,
            "lessons_per_subject_per_week": lessons_per_subject,
            "use_streams": use_streams,
            "exams_per_day": exams_per_day,
            "term_id": str(term.id) if term else None,
            "examination_session_id": str(session.id) if session else None,
        },
        slots=slots,
        stats=stats,
        warnings=warnings,
        expires_at=expires,
    )
    return draft


def regenerate_draft(*, draft: TimetableGenerationDraft, user) -> TimetableGenerationDraft:
    assert_timetable_write(user)
    if draft.expires_at and draft.expires_at < timezone.now():
        raise ValidationError({"detail": "This draft has expired. Generate a new one."})
    new_seed = (int(draft.seed) + random.randint(1, 10_000)) % (2**31)
    return create_generation_draft(
        tenant=draft.tenant,
        user=user,
        schedule_type=draft.schedule_type,
        config=draft.config or {},
        seed=new_seed,
    )


@transaction.atomic
def apply_generation_draft(*, draft: TimetableGenerationDraft, user) -> TimetableSchedule:
    """USE IT — persist slots as an active locked schedule for the term/session."""
    assert_timetable_write(user)
    if draft.expires_at and draft.expires_at < timezone.now():
        raise ValidationError({"detail": "This draft has expired. Generate again before applying."})
    if not draft.slots:
        raise ValidationError({"detail": "Draft has no slots to apply."})

    tenant = draft.tenant
    schedule_type = draft.schedule_type

    # Archive previous active schedule for same scope
    prev = TimetableSchedule.objects.filter(
        tenant=tenant,
        schedule_type=schedule_type,
        status=TimetableSchedule.STATUS_ACTIVE,
        is_deleted=False,
    )
    if schedule_type == TimetableSchedule.SCHEDULE_LESSON and draft.term_id:
        prev = prev.filter(term_id=draft.term_id)
    if schedule_type == TimetableSchedule.SCHEDULE_EXAM and draft.examination_session_id:
        prev = prev.filter(examination_session_id=draft.examination_session_id)
    for old in prev:
        old.status = TimetableSchedule.STATUS_ARCHIVED
        old.is_locked = True
        old.save(update_fields=["status", "is_locked", "updated_at"])
        # Soft-delete old entries
        Timetable.objects.filter(tenant=tenant, schedule=old, is_deleted=False).update(
            is_deleted=True, updated_at=timezone.now(),
        )

    schedule = TimetableSchedule.objects.create(
        tenant=tenant,
        created_by=user,
        updated_by=user,
        name=draft.name or "Timetable",
        schedule_type=schedule_type,
        academic_year=draft.academic_year,
        term=draft.term,
        examination_session=draft.examination_session,
        status=TimetableSchedule.STATUS_ACTIVE,
        is_locked=True,
        generation_seed=draft.seed,
        config=draft.config or {},
        stats=draft.stats or {},
        applied_at=timezone.now(),
        applied_by=user,
    )

    entries = []
    for slot in draft.slots:
        exam_date = None
        if slot.get("exam_date"):
            exam_date = date.fromisoformat(slot["exam_date"])
        entries.append(Timetable(
            tenant=tenant,
            created_by=user,
            updated_by=user,
            schedule=schedule,
            school_class_id=slot["school_class_id"],
            stream_id=slot.get("stream_id"),
            subject_id=slot["subject_id"],
            teacher_id=slot.get("teacher_id"),
            period_id=slot.get("period_id"),
            term=draft.term,
            examination_session=draft.examination_session,
            schedule_type=schedule_type,
            day_of_week=slot.get("day_of_week"),
            exam_date=exam_date,
            start_time=_parse_time(slot["start_time"]),
            end_time=_parse_time(slot["end_time"]),
            room=slot.get("room") or "",
        ))
    Timetable.objects.bulk_create(entries, batch_size=500)

    # Expire draft
    draft.expires_at = timezone.now()
    draft.save(update_fields=["expires_at", "updated_at"])

    return schedule


def serialize_draft(draft: TimetableGenerationDraft) -> dict[str, Any]:
    return {
        "id": str(draft.id),
        "schedule_type": draft.schedule_type,
        "name": draft.name,
        "seed": draft.seed,
        "config": draft.config,
        "slots": draft.slots,
        "stats": draft.stats,
        "warnings": draft.warnings,
        "term_id": str(draft.term_id) if draft.term_id else None,
        "examination_session_id": str(draft.examination_session_id) if draft.examination_session_id else None,
        "academic_year_id": str(draft.academic_year_id) if draft.academic_year_id else None,
        "expires_at": draft.expires_at.isoformat() if draft.expires_at else None,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


def serialize_schedule(schedule: TimetableSchedule, *, user=None) -> dict[str, Any]:
    entries_qs = schedule.entries.filter(is_deleted=False)
    entry_count = entries_qs.count()
    teaching_count = entries_qs.filter(is_break_slot=False, subject__isnull=False).count()
    class_rows = list(
        entries_qs.exclude(school_class_id=None)
        .values("school_class_id", "school_class__name")
        .distinct()
    )
    class_ids = [r["school_class_id"] for r in class_rows]
    # Unique names preserving order
    seen_names = set()
    class_names = []
    for r in class_rows:
        n = r.get("school_class__name") or ""
        if n and n not in seen_names:
            seen_names.add(n)
            class_names.append(n)
        if len(class_names) >= 12:
            break
    is_admin = bool(user and user_is_school_admin(user))
    is_pub = schedule.is_published
    can_write = False
    if user is not None:
        if is_admin:
            can_write = True
        else:
            can_write = user_can_access_feature(
                getattr(user, "tenant", None), user, "timetables", require_write=True,
            )
    # Draft: any writer may edit. Published: school admin only.
    can_edit = bool(can_write and (not is_pub or is_admin))
    can_delete = bool(is_admin or (can_write and not is_pub))
    can_unpublish = bool(is_admin and is_pub)
    can_publish = bool(can_write and not is_pub and entry_count > 0)

    creator = getattr(schedule, "created_by", None)
    creator_name = ""
    if creator is not None:
        creator_name = (
            (getattr(creator, "get_full_name", None) and creator.get_full_name())
            or getattr(creator, "email", "")
            or str(getattr(creator, "id", ""))
        )
    publisher = getattr(schedule, "published_by", None)
    publisher_name = ""
    if publisher is not None:
        publisher_name = (
            (getattr(publisher, "get_full_name", None) and publisher.get_full_name())
            or getattr(publisher, "email", "")
            or ""
        )

    return {
        "id": str(schedule.id),
        "name": schedule.name,
        "schedule_type": schedule.schedule_type,
        "status": schedule.status,
        "is_published": is_pub,
        "is_locked": schedule.is_locked,
        "term_id": str(schedule.term_id) if schedule.term_id else None,
        "term_name": schedule.term.name if schedule.term_id else "",
        "academic_year_name": (
            schedule.academic_year.name if schedule.academic_year_id else ""
        ),
        "examination_session_id": str(schedule.examination_session_id) if schedule.examination_session_id else None,
        "examination_session_name": (
            schedule.examination_session.name if schedule.examination_session_id else ""
        ),
        "academic_year_id": str(schedule.academic_year_id) if schedule.academic_year_id else None,
        "generation_seed": schedule.generation_seed,
        "config": schedule.config,
        "stats": schedule.stats,
        "entry_count": entry_count,
        "teaching_count": teaching_count,
        "class_count": len(class_ids),
        "class_names": [n for n in class_names if n],
        "applied_at": schedule.applied_at.isoformat() if schedule.applied_at else None,
        "published_at": schedule.published_at.isoformat() if getattr(schedule, "published_at", None) else None,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
        "created_by_name": creator_name,
        "published_by_name": publisher_name,
        "permissions": {
            "can_edit": can_edit,
            "can_delete": can_delete,
            "can_publish": can_publish,
            "can_unpublish": can_unpublish,
            "can_print": True,
            "can_preview": True,
        },
    }
