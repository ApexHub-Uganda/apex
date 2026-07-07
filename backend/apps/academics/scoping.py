"""Academic data scoping by portal role and teaching assignments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.db import models
from django.db.models import Q

from apps.core.constants import UserRole, normalize_role
from apps.tenants.role_permissions import user_is_school_admin


@dataclass
class AcademicContext:
    user: Any
    tenant: Any
    role: str
    teacher: Any | None = None
    staff: Any | None = None
    is_school_wide: bool = False
    is_dos: bool = False
    is_hod: bool = False
    is_class_teacher: bool = False
    assigned_subject_ids: set = field(default_factory=set)
    assigned_class_ids: set = field(default_factory=set)
    class_teacher_class_ids: set = field(default_factory=set)
    department_id: UUID | None = None
    department_subject_ids: set = field(default_factory=set)
    teaching_pairs: set = field(default_factory=set)


def get_teacher_for_user(user) -> Any | None:
    staff = getattr(user, "staff_profile", None)
    if staff is None:
        return None
    return getattr(staff, "teacher_profile", None)


def user_has_school_wide_academic_access(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    role = normalize_role(getattr(user, "role", ""))
    return role == UserRole.DIRECTOR_OF_STUDIES


def get_academic_context(user) -> AcademicContext | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None

    tenant = getattr(user, "tenant", None)
    role = normalize_role(getattr(user, "role", ""))
    staff = getattr(user, "staff_profile", None)
    teacher = get_teacher_for_user(user)

    ctx = AcademicContext(
        user=user,
        tenant=tenant,
        role=role,
        teacher=teacher,
        staff=staff,
        is_school_wide=user_has_school_wide_academic_access(user),
        is_dos=role == UserRole.DIRECTOR_OF_STUDIES,
        is_hod=role == UserRole.HEAD_OF_DEPARTMENT,
    )

    if ctx.is_school_wide:
        return ctx

    if teacher is None and role not in (UserRole.HEAD_OF_DEPARTMENT,):
        return ctx

    from apps.academics.models import Assignment, Class, Homework, Subject, Timetable

    if teacher is not None:
        subject_ids = set(teacher.subjects.values_list("id", flat=True))
        timetable_rows = Timetable.objects.filter(
            tenant=tenant,
            teacher=teacher,
        ).values_list("subject_id", "school_class_id")
        for subject_id, class_id in timetable_rows:
            if subject_id:
                subject_ids.add(subject_id)
            if class_id:
                ctx.assigned_class_ids.add(class_id)
            if subject_id and class_id:
                ctx.teaching_pairs.add((subject_id, class_id))

        for model in (Assignment, Homework):
            rows = model.objects.filter(tenant=tenant, teacher=teacher).values_list(
                "subject_id", "school_class_id",
            )
            for subject_id, class_id in rows:
                if subject_id:
                    subject_ids.add(subject_id)
                if class_id:
                    ctx.assigned_class_ids.add(class_id)
                if subject_id and class_id:
                    ctx.teaching_pairs.add((subject_id, class_id))

        ctx.assigned_subject_ids = subject_ids
        ctx.class_teacher_class_ids = set(
            Class.objects.filter(tenant=tenant, class_teacher=teacher).values_list("id", flat=True),
        )
        ctx.is_class_teacher = bool(ctx.class_teacher_class_ids)

    if role == UserRole.HEAD_OF_DEPARTMENT and staff is not None:
        department = getattr(staff, "department", None)
        if department is None:
            from apps.academics.models import Department
            department = Department.objects.filter(tenant=tenant, head=staff).first()
        if department is not None:
            ctx.department_id = department.id
            ctx.department_subject_ids = set(
                Subject.objects.filter(tenant=tenant, department_id=department.id).values_list("id", flat=True),
            )
            if ctx.department_subject_ids:
                ctx.assigned_subject_ids |= ctx.department_subject_ids
                dept_class_ids = set(
                    Timetable.objects.filter(
                        tenant=tenant,
                        subject_id__in=ctx.department_subject_ids,
                    ).values_list("school_class_id", flat=True),
                )
                ctx.assigned_class_ids |= dept_class_ids

    return ctx


def _visible_class_ids(ctx: AcademicContext) -> set:
    return set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)


def _class_filter(ctx: AcademicContext) -> Q | None:
    class_ids = _visible_class_ids(ctx)
    if not class_ids:
        return None
    return Q(id__in=class_ids)


def _subject_filter(ctx: AcademicContext) -> Q | None:
    if ctx.assigned_subject_ids:
        return Q(id__in=ctx.assigned_subject_ids)
    if ctx.is_hod:
        return Q(pk__in=[])
    return Q(pk__in=[])


def _exam_filter(ctx: AcademicContext) -> Q:
    if ctx.teaching_pairs:
        pair_query = Q()
        for subject_id, class_id in ctx.teaching_pairs:
            pair_query |= Q(subject_id=subject_id, school_class_id=class_id)
        return pair_query
    if ctx.assigned_subject_ids and ctx.assigned_class_ids:
        return Q(
            subject_id__in=ctx.assigned_subject_ids,
            school_class_id__in=ctx.assigned_class_ids,
        )
    return Q(pk__in=[])


def filter_queryset_for_user(queryset: models.QuerySet, user) -> models.QuerySet:
    ctx = get_academic_context(user)
    if ctx is None:
        return queryset.none()
    if ctx.is_school_wide:
        return queryset

    model = queryset.model
    model_name = model.__name__

    if model_name == "Subject":
        clause = _subject_filter(ctx)
        return queryset.filter(clause) if clause is not None else queryset.none()

    if model_name == "Class":
        clause = _class_filter(ctx)
        return queryset.filter(clause) if clause is not None else queryset.none()

    if model_name == "Stream":
        class_ids = _visible_class_ids(ctx)
        if not class_ids:
            return queryset.none()
        return queryset.filter(school_class_id__in=class_ids)

    if model_name == "Exam":
        return queryset.filter(_exam_filter(ctx))

    if model_name == "Grade":
        from apps.examinations.models import Exam
        exam_ids = Exam.objects.filter(_exam_filter(ctx)).values_list("id", flat=True)
        return queryset.filter(exam_id__in=exam_ids)

    if model_name == "ReportCard":
        class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
        if not class_ids:
            return queryset.none()
        return queryset.filter(school_class_id__in=class_ids)

    if model_name == "Student":
        class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
        if not class_ids:
            return queryset.none()
        return queryset.filter(school_class_id__in=class_ids)

    if model_name == "AttendanceRecord":
        class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
        if not class_ids:
            return queryset.filter(attendee_type="staff", staff=ctx.staff) if ctx.staff else queryset.none()
        return queryset.filter(
            Q(attendee_type="student", student__school_class_id__in=class_ids)
            | Q(attendee_type="staff", staff=ctx.staff),
        )

    if model_name in ("Timetable", "Assignment", "Homework"):
        if ctx.teacher is not None:
            return queryset.filter(teacher=ctx.teacher)
        if ctx.is_hod and ctx.department_subject_ids:
            return queryset.filter(subject_id__in=ctx.department_subject_ids)
        return queryset.none()

    if model_name == "Term":
        return queryset

    if model_name == "AcademicYear":
        return queryset.none()

    if model_name == "ClassNotice":
        class_ids = set(ctx.class_teacher_class_ids)
        if ctx.is_hod or ctx.teacher is not None:
            class_ids |= set(ctx.assigned_class_ids)
        if not class_ids:
            return queryset.none()
        return queryset.filter(school_class_id__in=class_ids)

    if model_name == "DisciplineRemark":
        class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
        if not class_ids:
            return queryset.none()
        qs = queryset.filter(school_class_id__in=class_ids)
        if ctx.is_hod and ctx.department_subject_ids:
            qs = qs.filter(
                Q(subject_id__isnull=True) | Q(subject_id__in=ctx.department_subject_ids),
            )
        return qs

    if model_name == "ExaminationSession":
        return queryset

    if model_name == "LessonAttendanceSession":
        if ctx.teacher is not None:
            return queryset.filter(teacher=ctx.teacher)
        class_ids = _visible_class_ids(ctx)
        if class_ids:
            return queryset.filter(school_class_id__in=class_ids)
        return queryset.none()

    if model_name == "LessonAttendanceEntry":
        from apps.attendance.models import LessonAttendanceSession

        session_ids = LessonAttendanceSession.objects.filter(
            tenant=ctx.tenant,
        )
        session_ids = filter_queryset_for_user(session_ids, user).values_list("id", flat=True)
        return queryset.filter(session_id__in=session_ids)

    return queryset


def user_can_access_exam(user, exam) -> bool:
    ctx = get_academic_context(user)
    if ctx is None:
        return False
    if ctx.is_school_wide:
        return True
    pair = (exam.subject_id, exam.school_class_id)
    if pair in ctx.teaching_pairs:
        return True
    if (
        exam.subject_id in ctx.assigned_subject_ids
        and exam.school_class_id in ctx.assigned_class_ids
    ):
        return True
    if ctx.is_hod and exam.subject_id in ctx.department_subject_ids:
        return True
    return False


def user_can_access_class(user, class_id) -> bool:
    ctx = get_academic_context(user)
    if ctx is None:
        return False
    if ctx.is_school_wide:
        return True
    try:
        normalized = UUID(str(class_id))
    except (TypeError, ValueError):
        return False
    return normalized in ctx.assigned_class_ids or normalized in ctx.class_teacher_class_ids


def scoped_subject_ids(user) -> set | None:
    """Return None when school-wide; otherwise assigned subject ids."""
    ctx = get_academic_context(user)
    if ctx is None:
        return set()
    if ctx.is_school_wide:
        return None
    return set(ctx.assigned_subject_ids)


def scoped_class_ids(user) -> set | None:
    ctx = get_academic_context(user)
    if ctx is None:
        return set()
    if ctx.is_school_wide:
        return None
    return set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)