"""
Examination timetable builder.

Unlike lesson timetables (day-of-week × period), exam slots capture a concrete
**date** and time. Invigilators/teachers are free-picked (not forced from
teaching assignments). Constraints respect other published lesson/exam schedules.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.academics.models import Class, Period, Subject, Term, Timetable, TimetableSchedule
from apps.academics.services.timetable_builder import _teacher_name, serialize_period
from apps.academics.singleton import get_active_academic_year, get_active_term
from apps.academics.timetable_generator import DAY_LABELS, assert_timetable_write, serialize_schedule
from apps.staff.models import Teacher
from apps.tenants.role_permissions import user_is_school_admin


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _parse_time(value) -> time:
    if isinstance(value, time):
        return value
    s = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s[:8], fmt).time()
        except ValueError:
            continue
    raise ValidationError(f'Invalid time "{value}". Use HH:MM.')


def create_draft_exam_schedule(
    *,
    tenant,
    user,
    examination_session_id: str | None = None,
    term_id: str | None = None,
    name: str = "",
) -> TimetableSchedule:
    assert_timetable_write(user)
    session = None
    term = None
    academic_year = get_active_academic_year(tenant)

    if examination_session_id:
        from apps.examinations.models import ExaminationSession
        session = ExaminationSession.objects.filter(
            tenant=tenant, pk=examination_session_id, is_deleted=False,
        ).select_related("term", "academic_year").first()
        if not session:
            raise ValidationError("Examination session not found.")
        term = session.term
        academic_year = session.academic_year or academic_year
    if term is None and term_id:
        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
    if term is None:
        term = get_active_term(tenant)

    base = (name or "").strip() or (
        f"{session.name} Exam Timetable" if session else f"{(term.name if term else 'Exam')} Exam Timetable"
    )
    existing = set(
        TimetableSchedule.objects.filter(
            tenant=tenant, schedule_type=TimetableSchedule.SCHEDULE_EXAM, is_deleted=False,
        ).values_list("name", flat=True)
    )
    final = base
    n = 2
    while final in existing:
        final = f"{base} ({n})"
        n += 1

    return TimetableSchedule.objects.create(
        tenant=tenant,
        created_by=user,
        updated_by=user,
        name=final,
        schedule_type=TimetableSchedule.SCHEDULE_EXAM,
        academic_year=academic_year,
        term=term,
        examination_session=session,
        status=TimetableSchedule.STATUS_DRAFT,
        is_locked=False,
        applied_at=timezone.now(),
        applied_by=user,
        config={"source": "exam_timetable_builder"},
        stats={"entry_count": 0},
    )


def build_exam_wizard_context(*, tenant, user) -> dict[str, Any]:
    from apps.examinations.models import ExaminationSession

    term = get_active_term(tenant)
    year = get_active_academic_year(tenant)
    sessions = list(
        ExaminationSession.objects.filter(tenant=tenant, is_deleted=False)
        .exclude(status="closed")
        .order_by("-start_date")[:30]
    )
    periods = list(
        Period.objects.filter(tenant=tenant, is_deleted=False, is_break=False)
        .order_by("sort_order", "start_time")
    )
    classes = list(
        Class.objects.filter(tenant=tenant, is_deleted=False).order_by("name")
    )
    if year:
        classes = list(
            Class.objects.filter(tenant=tenant, is_deleted=False, academic_year=year).order_by("name")
        )
    subjects = list(Subject.objects.filter(tenant=tenant, is_deleted=False).order_by("name"))
    teachers = list(
        Teacher.objects.filter(tenant=tenant, is_deleted=False)
        .select_related("staff")
        .order_by("staff__last_name", "staff__first_name")
    )

    # Published occupancy snapshot for UI hints
    published = Timetable.objects.filter(
        tenant=tenant,
        is_deleted=False,
        is_break_slot=False,
        schedule__status__in=[TimetableSchedule.STATUS_PUBLISHED, TimetableSchedule.STATUS_ACTIVE],
        schedule__is_deleted=False,
    ).select_related("school_class", "teacher__staff", "subject", "period", "schedule")[:500]

    busy_hints = []
    for e in published:
        busy_hints.append({
            "teacher_id": str(e.teacher_id) if e.teacher_id else None,
            "teacher_name": _teacher_name(e.teacher) if e.teacher_id else "",
            "day_of_week": e.day_of_week,
            "exam_date": str(e.exam_date) if e.exam_date else None,
            "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
            "end_time": e.end_time.strftime("%H:%M") if e.end_time else "",
            "class_name": e.school_class.name if e.school_class_id else "",
            "subject": e.display_subject or (e.subject.name if e.subject_id else ""),
            "schedule_type": e.schedule_type,
            "schedule_name": e.schedule.name if e.schedule_id else "",
        })

    from apps.academics.scoping import get_teacher_for_user

    viewer_teacher = get_teacher_for_user(user)
    return {
        "active_term": (
            {"id": str(term.id), "name": term.name} if term else None
        ),
        "academic_year": (
            {"id": str(year.id), "name": year.name} if year else None
        ),
        "examination_sessions": [
            {
                "id": str(s.id),
                "name": s.name,
                "start_date": str(s.start_date),
                "end_date": str(s.end_date),
                "status": s.status,
                "term_id": str(s.term_id) if s.term_id else None,
            }
            for s in sessions
        ],
        "periods": [serialize_period(p) for p in periods],
        "classes": [
            {"id": str(c.id), "name": c.name, "code": c.code, "room": c.room or ""}
            for c in classes
        ],
        "subjects": [
            {"id": str(s.id), "name": s.name, "code": s.code} for s in subjects
        ],
        "teachers": [
            {"id": str(t.id), "name": _teacher_name(t)}
            for t in teachers if t.staff_id
        ],
        "published_busy": busy_hints[:200],
        "is_school_admin": user_is_school_admin(user),
        "viewer_teacher_id": str(viewer_teacher.id) if viewer_teacher else None,
        "viewer_teacher_name": _teacher_name(viewer_teacher) if viewer_teacher else "",
    }


def get_exam_schedule_slots(*, tenant, schedule_id: str) -> dict[str, Any]:
    schedule = TimetableSchedule.objects.filter(
        tenant=tenant, pk=schedule_id, is_deleted=False,
        schedule_type=TimetableSchedule.SCHEDULE_EXAM,
    ).select_related("term", "examination_session", "created_by", "published_by").first()
    if not schedule:
        raise ValidationError("Exam timetable not found.")
    entries = (
        Timetable.objects.filter(tenant=tenant, schedule=schedule, is_deleted=False)
        .select_related("school_class", "subject", "teacher__staff", "period")
        .order_by("exam_date", "start_time", "school_class__name")
    )
    slots = []
    for e in entries:
        slots.append({
            "id": str(e.id),
            "exam_date": str(e.exam_date) if e.exam_date else None,
            "day_of_week": e.day_of_week,
            "day_label": DAY_LABELS.get(e.day_of_week or 0, ""),
            "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
            "end_time": e.end_time.strftime("%H:%M") if e.end_time else "",
            "period_id": str(e.period_id) if e.period_id else None,
            "school_class_id": str(e.school_class_id) if e.school_class_id else None,
            "school_class_name": e.school_class.name if e.school_class_id else "",
            "subject_id": str(e.subject_id) if e.subject_id else None,
            "subject_name": e.display_subject or (e.subject.name if e.subject_id else ""),
            "teacher_id": str(e.teacher_id) if e.teacher_id else None,
            "teacher_name": e.display_teacher or (_teacher_name(e.teacher) if e.teacher_id else ""),
            "room": e.room or "",
        })
    return {
        "schedule": serialize_schedule(schedule),
        "slots": slots,
    }


def validate_exam_slots(*, tenant, slots: list[dict], schedule_id: str | None = None) -> dict[str, Any]:
    conflicts = []
    teacher_local: dict[tuple, list] = defaultdict(list)
    class_local: dict[tuple, list] = defaultdict(list)

    # Published busy (lessons by weekday+time window, exams by date+time)
    published = Timetable.objects.filter(
        tenant=tenant,
        is_deleted=False,
        is_break_slot=False,
        schedule__status__in=[TimetableSchedule.STATUS_PUBLISHED, TimetableSchedule.STATUS_ACTIVE],
        schedule__is_deleted=False,
    ).exclude(schedule_id=schedule_id).select_related(
        "school_class", "teacher__staff", "subject", "schedule",
    )

    pub_teacher_date: dict[tuple, dict] = {}
    pub_teacher_weekday: dict[tuple, dict] = {}
    for e in published:
        if not e.teacher_id or not e.start_time or not e.end_time:
            continue
        info = {
            "class_name": e.school_class.name if e.school_class_id else "",
            "subject": e.display_subject or (e.subject.name if e.subject_id else ""),
            "schedule": e.schedule.name if e.schedule_id else "",
            "start": e.start_time.strftime("%H:%M"),
            "end": e.end_time.strftime("%H:%M"),
        }
        if e.exam_date:
            pub_teacher_date[(str(e.teacher_id), str(e.exam_date), e.start_time.strftime("%H:%M"))] = info
        elif e.day_of_week is not None:
            pub_teacher_weekday[(str(e.teacher_id), e.day_of_week, e.start_time.strftime("%H:%M"))] = info

    def overlaps(a0: time, a1: time, b0: time, b1: time) -> bool:
        return a0 < b1 and b0 < a1

    for i, slot in enumerate(slots):
        if not slot.get("exam_date") or not slot.get("start_time") or not slot.get("end_time"):
            continue
        if not slot.get("school_class_id") and not slot.get("school_class"):
            continue
        try:
            ed = _parse_date(slot["exam_date"])
            st = _parse_time(slot["start_time"])
            et = _parse_time(slot["end_time"])
        except ValidationError as exc:
            conflicts.append({"type": "invalid", "index": i, "message": str(exc.detail)})
            continue
        if et <= st:
            conflicts.append({
                "type": "invalid",
                "index": i,
                "message": f"Row {i + 1}: end time must be after start.",
            })
            continue

        class_id = str(slot.get("school_class_id") or slot.get("school_class"))
        teacher_id = slot.get("teacher_id") or slot.get("teacher")
        if teacher_id in ("", "null", "undefined", None):
            teacher_id = None
        else:
            teacher_id = str(teacher_id)

        class_local[(str(ed), st.strftime("%H:%M"), class_id)].append(i)
        if teacher_id:
            teacher_local[(str(ed), st.strftime("%H:%M"), teacher_id)].append(i)
            # vs published exam same date/time
            key = (teacher_id, str(ed), st.strftime("%H:%M"))
            if key in pub_teacher_date:
                c = pub_teacher_date[key]
                conflicts.append({
                    "type": "teacher_clash_published",
                    "index": i,
                    "message": (
                        f"Teacher already assigned on {ed} at {st.strftime('%H:%M')} "
                        f"({c['subject']} / {c['class_name']}) in published “{c['schedule']}”."
                    ),
                })
            # vs published lesson same weekday/time
            wd = ed.weekday()
            wk = (teacher_id, wd, st.strftime("%H:%M"))
            if wk in pub_teacher_weekday:
                c = pub_teacher_weekday[wk]
                conflicts.append({
                    "type": "teacher_clash_lesson",
                    "index": i,
                    "message": (
                        f"Teacher has a published lesson on {DAY_LABELS.get(wd, '')}s "
                        f"at {st.strftime('%H:%M')} ({c['subject']} / {c['class_name']})."
                    ),
                })

    for key, idxs in class_local.items():
        if len(idxs) > 1:
            conflicts.append({
                "type": "class_double",
                "indexes": idxs,
                "message": f"Same class has overlapping exam sittings on {key[0]} at {key[1]}.",
            })
    for key, idxs in teacher_local.items():
        if len(idxs) > 1:
            conflicts.append({
                "type": "teacher_double",
                "indexes": idxs,
                "message": f"Same teacher invigilates more than one exam on {key[0]} at {key[1]}.",
            })

    return {
        "ok": len(conflicts) == 0,
        "conflicts": conflicts,
        "stats": {"slots": len(slots), "conflict_count": len(conflicts)},
    }


@transaction.atomic
def save_exam_slots(
    *,
    tenant,
    user,
    schedule_id: str,
    slots: list[dict],
    force: bool = False,
) -> dict[str, Any]:
    assert_timetable_write(user)
    schedule = TimetableSchedule.objects.filter(
        tenant=tenant, pk=schedule_id, is_deleted=False,
        schedule_type=TimetableSchedule.SCHEDULE_EXAM,
    ).first()
    if not schedule:
        raise ValidationError("Exam timetable not found.")
    if schedule.is_published and not user_is_school_admin(user):
        raise ValidationError("Published exam timetable — only school admin can edit.")

    validation = validate_exam_slots(tenant=tenant, slots=slots, schedule_id=str(schedule.id))
    if validation["conflicts"] and not force:
        raise ValidationError({
            "conflicts": validation["conflicts"],
            "detail": "Resolve conflicts or save with force=true.",
        })

    Timetable.objects.filter(tenant=tenant, schedule=schedule, is_deleted=False).update(
        is_deleted=True, updated_by=user, updated_at=timezone.now(),
    )

    created = 0
    for slot in slots:
        if not slot.get("exam_date") or not slot.get("start_time") or not slot.get("end_time"):
            continue
        class_id = slot.get("school_class_id") or slot.get("school_class")
        subject_id = slot.get("subject_id") or slot.get("subject")
        if not class_id or not subject_id:
            continue
        ed = _parse_date(slot["exam_date"])
        st = _parse_time(slot["start_time"])
        et = _parse_time(slot["end_time"])
        if et <= st:
            continue

        school_class = Class.objects.filter(tenant=tenant, pk=class_id, is_deleted=False).first()
        subject = Subject.objects.filter(tenant=tenant, pk=subject_id, is_deleted=False).first()
        if not school_class or not subject:
            raise ValidationError("Invalid class or subject on an exam row.")

        teacher = None
        teacher_id = slot.get("teacher_id") or slot.get("teacher")
        if teacher_id and teacher_id not in ("", "null", "undefined"):
            teacher = Teacher.objects.filter(tenant=tenant, pk=teacher_id, is_deleted=False).first()

        period = None
        if slot.get("period_id"):
            period = Period.objects.filter(tenant=tenant, pk=slot["period_id"], is_deleted=False).first()

        display_subject = (slot.get("subject_name") or subject.name or "")[:120]
        display_teacher = (slot.get("teacher_name") or _teacher_name(teacher) or "")[:120]

        Timetable.objects.create(
            tenant=tenant,
            created_by=user,
            updated_by=user,
            schedule=schedule,
            school_class=school_class,
            subject=subject,
            teacher=teacher,
            period=period,
            term=schedule.term,
            examination_session=schedule.examination_session,
            schedule_type=TimetableSchedule.SCHEDULE_EXAM,
            day_of_week=ed.weekday(),
            exam_date=ed,
            start_time=st,
            end_time=et,
            room=(slot.get("room") or school_class.room or "")[:50],
            is_break_slot=False,
            slot_label="",
            display_subject=display_subject,
            display_teacher=display_teacher,
        )
        created += 1

    schedule.stats = {
        **(schedule.stats or {}),
        "entry_count": created,
        "last_saved_at": timezone.now().isoformat(),
    }
    schedule.updated_by = user
    schedule.save(update_fields=["stats", "updated_by", "updated_at"])
    return {
        "schedule_id": str(schedule.id),
        "entries_created": created,
        "validation": validation,
        "is_published": schedule.is_published,
        "schedule_status": schedule.status,
    }


def publish_exam_schedule(*, tenant, user, schedule_id: str) -> dict[str, Any]:
    assert_timetable_write(user)
    schedule = TimetableSchedule.objects.filter(
        tenant=tenant, pk=schedule_id, is_deleted=False,
        schedule_type=TimetableSchedule.SCHEDULE_EXAM,
    ).first()
    if not schedule:
        raise ValidationError("Exam timetable not found.")
    n = Timetable.objects.filter(schedule=schedule, is_deleted=False).count()
    if n == 0:
        raise ValidationError("Cannot publish an empty exam timetable.")
    schedule.status = TimetableSchedule.STATUS_PUBLISHED
    schedule.is_locked = True
    schedule.published_at = timezone.now()
    schedule.published_by = user
    schedule.updated_by = user
    schedule.save(update_fields=[
        "status", "is_locked", "published_at", "published_by", "updated_by", "updated_at",
    ])
    return serialize_schedule(schedule, user=user)


def build_exam_timetable_pdf(
    *,
    tenant,
    schedule_id: str,
    orientation: str = "landscape",
    request=None,
    teacher_mode: str | None = None,
    teacher_id: str | None = None,
) -> bytes:
    from reportlab.platypus import Spacer, Table, TableStyle
    from reportlab.lib import colors
    from apps.core.pdf_template import branded_table_style, build_branded_pdf, p
    from apps.core.exports import escape_pdf_text
    from reportlab.platypus import Paragraph

    mode = (teacher_mode or "").strip().lower()
    if mode in ("", "all", "none", "off"):
        mode = ""
    if mode not in ("", "highlight", "mine_only"):
        mode = ""
    focus_teacher_id = str(teacher_id) if teacher_id else ""
    if mode and not focus_teacher_id and request is not None:
        from apps.academics.scoping import get_teacher_for_user
        viewer = get_teacher_for_user(getattr(request, "user", None))
        if viewer is not None:
            focus_teacher_id = str(viewer.id)
    if mode and not focus_teacher_id:
        mode = ""

    schedule = TimetableSchedule.objects.filter(
        tenant=tenant, pk=schedule_id, is_deleted=False,
    ).select_related(
        "term", "examination_session", "created_by", "published_by",
    ).first()
    if not schedule:
        raise ValueError("Exam timetable not found.")

    entries = list(
        Timetable.objects.filter(tenant=tenant, schedule=schedule, is_deleted=False)
        .select_related("school_class", "subject", "teacher__staff")
        .order_by("exam_date", "start_time", "school_class__name")
    )

    creator = schedule.created_by
    creator_name = ""
    if creator:
        creator_name = getattr(creator, "get_full_name", lambda: "")() or getattr(creator, "email", "") or ""

    class_names = sorted({
        e.school_class.name for e in entries if e.school_class_id and e.school_class
    })
    if len(class_names) == 1:
        class_label = class_names[0]
    elif len(class_names) <= 3:
        class_label = ", ".join(class_names)
    elif class_names:
        class_label = f"{len(class_names)} classes"
    else:
        class_label = ""
    # Compact professional QR: school (envelope) + name, status, term, class
    qr_meta = {
        "name": (schedule.name or "Exam Timetable")[:80],
        "status": schedule.status or "draft",
        "term": (
            schedule.examination_session.name
            if schedule.examination_session_id
            else (schedule.term.name if schedule.term_id else "")
        )[:80],
        "class": class_label[:80],
    }

    MINE_BG = colors.HexColor("#FEF3C7")
    subtitle = (
        schedule.examination_session.name
        if schedule.examination_session_id
        else (schedule.term.name if schedule.term_id else "Examination")
    )
    if mode == "highlight":
        subtitle = f"{subtitle} · Your sittings highlighted"
    elif mode == "mine_only":
        subtitle = f"{subtitle} · Your sittings only"

    def story(ctx, styles):
        flow = []
        if schedule.examination_session_id:
            sess = schedule.examination_session
            flow.append(p(
                f"Session: {sess.name} ({sess.start_date} → {sess.end_date})",
                styles["Meta"],
            ))
        if mode == "highlight":
            flow.append(p("Highlighted rows are your invigilation sittings.", styles["Meta"]))
        elif mode == "mine_only":
            flow.append(p("Showing only your invigilation sittings.", styles["Meta"]))
        flow.append(Spacer(1, 6))
        rows = [[
            p("Date", styles["Label"]),
            p("Time", styles["Label"]),
            p("Class", styles["Label"]),
            p("Subject", styles["Label"]),
            p("Invigilator", styles["Label"]),
            p("Room", styles["Label"]),
        ]]
        mine_rows = []
        data_i = 0
        for e in entries:
            is_mine = bool(focus_teacher_id and e.teacher_id and str(e.teacher_id) == focus_teacher_id)
            if mode == "mine_only" and not is_mine:
                continue
            data_i += 1
            rows.append([
                p(str(e.exam_date) if e.exam_date else "—", styles["Small"]),
                p(
                    f"{e.start_time.strftime('%H:%M') if e.start_time else '—'}–"
                    f"{e.end_time.strftime('%H:%M') if e.end_time else '—'}",
                    styles["Small"],
                ),
                p(e.school_class.name if e.school_class_id else "—", styles["Small"]),
                p(e.display_subject or (e.subject.name if e.subject_id else "—"), styles["Small"]),
                p(e.display_teacher or "—", styles["Small"]),
                p(e.room or "—", styles["Small"]),
            ])
            if is_mine and mode in ("highlight", "mine_only"):
                mine_rows.append(data_i)
        if len(rows) == 1:
            flow.append(p(
                "No exam sittings scheduled." if mode != "mine_only"
                else "No invigilation sittings assigned to you on this timetable.",
                styles["Body"],
            ))
            return flow
        w = ctx.content_width
        col_w = [w * x for x in (0.16, 0.14, 0.14, 0.22, 0.22, 0.12)]
        table = Table(rows, colWidths=col_w, repeatRows=1)
        style_cmds = list(branded_table_style(ctx, header=True).getCommands())
        for ridx in mine_rows:
            style_cmds.append(("BACKGROUND", (0, ridx), (-1, ridx), MINE_BG))
        table.setStyle(TableStyle(style_cmds))
        flow.append(table)
        flow.append(Spacer(1, 10))
        flow.append(p(
            f"Created by {creator_name or '—'} · {len(rows) - 1} sitting(s).",
            styles["Meta"],
        ))
        return flow

    return build_branded_pdf(
        tenant=tenant,
        document_type="exam_timetable",
        document_meta=qr_meta,
        title=schedule.name or "Exam Timetable",
        subtitle=subtitle,
        build_story=story,
        request=request,
        orientation=orientation if orientation in ("portrait", "landscape") else "landscape",
    )
