"""Academic role workspace summaries."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.academics.models import Class, ClassNotice, DisciplineRemark, Homework, Timetable
from apps.academics.scoping import get_academic_context, user_has_school_wide_academic_access
from apps.attendance.models import LessonAttendanceSession
from apps.core.constants import UserRole, normalize_role
from apps.examinations.constants import MARKS_STATUS_DRAFT, MARKS_STATUS_SUBMITTED
from apps.examinations.models import Exam
from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin


def _feature_enabled(perms: dict, key: str) -> bool:
    return bool(perms.get(key, {}).get("can_read"))


def build_academic_workspace(*, tenant, user) -> dict[str, Any]:
    """Role-aware summary cards and queues for academic portal workspaces."""
    ctx = get_academic_context(user)
    role = normalize_role(getattr(user, "role", ""))
    perms = get_user_feature_permissions(tenant, user)
    is_school_wide = user_has_school_wide_academic_access(user) or user_is_school_admin(user)

    payload: dict[str, Any] = {
        "role": role,
        "is_class_teacher": role == UserRole.CLASS_TEACHER or bool(ctx and ctx.is_class_teacher),
        "is_school_wide": is_school_wide,
        "features": {
            key: perms.get(key, {"can_read": False, "can_write": False})
            for key in (
                "teacher_workspace", "class_teacher_tools", "hod_workspace", "dos_workspace",
                "marks_entry", "marks_approval", "assessment_management", "lesson_attendance",
                "class_notices", "discipline_remarks", "teacher_assignments", "examination_sessions",
            )
        },
        "counts": {},
        "queues": {},
        "quick_links": [],
    }

    if ctx is None and not is_school_wide:
        return payload

    exam_qs = Exam.objects.filter(tenant=tenant, is_deleted=False)
    if ctx and not is_school_wide:
        from apps.academics.scoping import filter_queryset_for_user
        exam_qs = filter_queryset_for_user(exam_qs, user)

    if _feature_enabled(perms, "marks_entry"):
        payload["counts"]["draft_marks"] = exam_qs.filter(
            lifecycle_status="published",
            marks_status=MARKS_STATUS_DRAFT,
        ).count()

    if _feature_enabled(perms, "marks_approval"):
        approval_qs = exam_qs.filter(marks_status=MARKS_STATUS_SUBMITTED).select_related(
            "subject", "school_class", "term",
        )[:20]
        payload["counts"]["pending_approval"] = exam_qs.filter(
            marks_status=MARKS_STATUS_SUBMITTED,
        ).count()
        payload["queues"]["marks_approval"] = [
            {
                "id": str(e.id),
                "name": e.name,
                "subject": e.subject.name if e.subject_id else "",
                "school_class": e.school_class.name if e.school_class_id else "",
                "term": e.term.name if e.term_id else "",
                "submitted_at": e.marks_submitted_at.isoformat() if e.marks_submitted_at else None,
            }
            for e in approval_qs
        ]

    if _feature_enabled(perms, "assessment_management"):
        payload["counts"]["draft_assessments"] = exam_qs.filter(lifecycle_status="draft").count()
        payload["queues"]["draft_assessments"] = [
            {
                "id": str(e.id),
                "name": e.name,
                "subject": e.subject.name if e.subject_id else "",
                "school_class": e.school_class.name if e.school_class_id else "",
                "exam_date": str(e.exam_date),
            }
            for e in exam_qs.filter(lifecycle_status="draft").select_related(
                "subject", "school_class",
            )[:20]
        ]

    class_ids: set = set()
    if ctx:
        class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
    if is_school_wide:
        class_ids = set(Class.objects.filter(tenant=tenant, is_deleted=False).values_list("id", flat=True))

    if class_ids:
        payload["counts"]["assigned_classes"] = len(class_ids)
        if _feature_enabled(perms, "class_notices") and ctx and (
            ctx.is_class_teacher or role == UserRole.CLASS_TEACHER
        ):
            notice_class_ids = ctx.class_teacher_class_ids or class_ids
            payload["counts"]["class_notices"] = ClassNotice.objects.filter(
                tenant=tenant,
                school_class_id__in=notice_class_ids,
                is_deleted=False,
            ).count()

    if ctx and ctx.teacher and _feature_enabled(perms, "lesson_attendance"):
        today = timezone.localdate()
        payload["counts"]["lesson_sessions_today"] = LessonAttendanceSession.objects.filter(
            tenant=tenant,
            teacher=ctx.teacher,
            date=today,
            is_deleted=False,
        ).count()

    if ctx and ctx.teacher:
        payload["counts"]["timetable_slots"] = Timetable.objects.filter(
            tenant=tenant,
            teacher=ctx.teacher,
            is_deleted=False,
        ).count()
        payload["counts"]["homework_items"] = Homework.objects.filter(
            tenant=tenant,
            teacher=ctx.teacher,
            is_deleted=False,
        ).count()

    if _feature_enabled(perms, "discipline_remarks") and class_ids:
        payload["counts"]["discipline_remarks"] = DisciplineRemark.objects.filter(
            tenant=tenant,
            school_class_id__in=class_ids,
            is_deleted=False,
        ).count()

    if role == UserRole.TEACHER and _feature_enabled(perms, "teacher_workspace"):
        payload["quick_links"] = [
            {"label": "Marks Entry", "path": "/school-admin/examinations/marks", "feature_key": "marks_entry"},
            {"label": "Lesson Attendance", "path": "/school-admin/attendance/lessons", "feature_key": "lesson_attendance"},
            {"label": "Homework", "path": "/school-admin/academics/homework", "feature_key": "homework"},
        ]
    elif role == UserRole.CLASS_TEACHER and _feature_enabled(perms, "class_teacher_tools"):
        payload["quick_links"] = [
            {"label": "Class Notices", "path": "/school-admin/academics/class-notices", "feature_key": "class_notices"},
            {"label": "Discipline", "path": "/school-admin/academics/discipline", "feature_key": "discipline_remarks"},
            {"label": "Marks Entry", "path": "/school-admin/examinations/marks", "feature_key": "marks_entry"},
            {"label": "Lesson Attendance", "path": "/school-admin/attendance/lessons", "feature_key": "lesson_attendance"},
        ]
    elif role == UserRole.HEAD_OF_DEPARTMENT and _feature_enabled(perms, "hod_workspace"):
        payload["quick_links"] = [
            {"label": "Marks Approval", "path": "/school-admin/examinations/approval", "feature_key": "marks_approval"},
            {"label": "Subjects", "path": "/school-admin/academics/subjects", "feature_key": "subjects"},
            {"label": "Assessments", "path": "/school-admin/examinations/assessments", "feature_key": "assessment_management"},
            {"label": "Marks Entry", "path": "/school-admin/examinations/marks", "feature_key": "marks_entry"},
            {"label": "Report Cards", "path": "/school-admin/examinations/report-cards", "feature_key": "report_cards"},
        ]
        if ctx and ctx.department_subject_ids:
            payload["counts"]["department_subjects"] = len(ctx.department_subject_ids)
            payload["counts"]["department_classes"] = len(ctx.assigned_class_ids or set())
    elif role == UserRole.DIRECTOR_OF_STUDIES and _feature_enabled(perms, "dos_workspace"):
        payload["quick_links"] = [
            {"label": "Teacher Assignments", "path": "/school-admin/academics/subject-assignments", "feature_key": "teacher_assignments"},
            {"label": "Exam Sessions", "path": "/school-admin/examinations/sessions", "feature_key": "examination_sessions"},
            {"label": "Marks Approval", "path": "/school-admin/examinations/approval", "feature_key": "marks_approval"},
            {"label": "Timetable Wizard", "path": "/school-admin/academics/timetable/wizard", "feature_key": "timetables"},
            {"label": "Terms", "path": "/school-admin/academics/terms", "feature_key": "terms"},
            {"label": "Assessments", "path": "/school-admin/examinations/assessments", "feature_key": "assessment_management"},
        ]
        from apps.academics.models import TeachingAssignment, Term
        from apps.examinations.models import ExaminationSession

        payload["counts"]["active_terms"] = Term.objects.filter(
            tenant=tenant, is_deleted=False, is_current=True,
        ).count()
        payload["counts"]["open_exam_sessions"] = ExaminationSession.objects.filter(
            tenant=tenant, is_deleted=False,
        ).exclude(status="closed").count()
        payload["counts"]["teaching_assignments"] = TeachingAssignment.objects.filter(
            tenant=tenant, is_deleted=False, is_active=True,
        ).count()

    if (
        role == UserRole.TEACHER
        and ctx
        and ctx.is_class_teacher
        and _feature_enabled(perms, "class_teacher_tools")
    ):
        payload["quick_links"].extend([
            {"label": "Class Notices", "path": "/school-admin/academics/class-notices", "feature_key": "class_notices"},
            {"label": "Discipline", "path": "/school-admin/academics/discipline", "feature_key": "discipline_remarks"},
        ])

    return payload