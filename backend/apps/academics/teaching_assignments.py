"""Teaching assignment helpers — sync teacher subject M2M from staffing rows."""
from __future__ import annotations

from typing import Any

from apps.academics.models import Class, Subject, TeachingAssignment
from apps.staff.models import Teacher
from apps.tenants.models import Tenant


def upsert_teaching_assignment(
    *,
    tenant: Tenant,
    teacher: Teacher,
    school_class: Class,
    subject: Subject,
    notes: str,
    user: Any,
) -> tuple[TeachingAssignment, str]:
    """Create or restore an active assignment row for teacher + class + subject."""
    row = TeachingAssignment.all_objects.filter(
        tenant=tenant,
        teacher=teacher,
        school_class=school_class,
        subject=subject,
    ).first()
    if row is not None:
        status = "restored" if row.is_deleted else "existing"
        row.is_deleted = False
        row.is_active = True
        row.academic_year = school_class.academic_year
        row.notes = notes or row.notes
        row.updated_by = user
        row.save(update_fields=[
            "is_deleted", "is_active", "academic_year", "notes", "updated_by", "updated_at",
        ])
        return row, status

    row = TeachingAssignment.objects.create(
        tenant=tenant,
        teacher=teacher,
        school_class=school_class,
        subject=subject,
        academic_year=school_class.academic_year,
        is_active=True,
        notes=notes,
        created_by=user,
        updated_by=user,
    )
    return row, "created"


def sync_teacher_class_subjects(
    *,
    tenant: Tenant,
    teacher: Teacher,
    school_class: Class,
    subjects: list[Subject],
    notes: str,
    user: Any,
) -> dict[str, int]:
    """Replace the subject set for one teacher + class staffing group."""
    target_ids = {subject.id for subject in subjects}
    existing = TeachingAssignment.objects.filter(
        tenant=tenant,
        teacher=teacher,
        school_class=school_class,
        is_active=True,
        is_deleted=False,
    ).select_related("subject")

    created = 0
    restored = 0
    removed = 0
    updated = 0

    for row in existing:
        if row.subject_id not in target_ids:
            row.soft_delete(user=user)
            removed += 1

    for subject in subjects:
        row, status = upsert_teaching_assignment(
            tenant=tenant,
            teacher=teacher,
            school_class=school_class,
            subject=subject,
            notes=notes,
            user=user,
        )
        if status == "created":
            created += 1
        elif status == "restored":
            restored += 1
        elif notes and row.notes != notes:
            updated += 1

    sync_teacher_subjects_from_assignments(teacher)
    return {
        "created_count": created,
        "restored_count": restored,
        "removed_count": removed,
        "updated_count": updated,
    }


def sync_teacher_assignments(
    *,
    tenant: Tenant,
    teacher: Teacher,
    pairs: list[tuple[Class, Subject]],
    notes: str,
    user: Any,
) -> dict[str, int]:
    """Replace the full class–subject assignment set for one teacher."""
    target_keys = {(school_class.id, subject.id) for school_class, subject in pairs}
    existing = TeachingAssignment.objects.filter(
        tenant=tenant,
        teacher=teacher,
        is_active=True,
        is_deleted=False,
    )

    created = 0
    restored = 0
    removed = 0
    updated = 0

    for row in existing:
        if (row.school_class_id, row.subject_id) not in target_keys:
            row.soft_delete(user=user)
            removed += 1

    for school_class, subject in pairs:
        row, status = upsert_teaching_assignment(
            tenant=tenant,
            teacher=teacher,
            school_class=school_class,
            subject=subject,
            notes=notes,
            user=user,
        )
        if status == "created":
            created += 1
        elif status == "restored":
            restored += 1
        elif notes and row.notes != notes:
            updated += 1

    sync_teacher_subjects_from_assignments(teacher)
    return {
        "created_count": created,
        "restored_count": restored,
        "removed_count": removed,
        "updated_count": updated,
    }


def sync_teacher_subjects_from_assignments(teacher: Teacher) -> None:
    """Keep Teacher.subjects aligned with active teaching assignment subjects."""
    subject_ids = (
        TeachingAssignment.objects.filter(
            tenant=teacher.tenant,
            teacher=teacher,
            is_active=True,
            is_deleted=False,
        )
        .values_list("subject_id", flat=True)
        .distinct()
    )
    teacher.subjects.set(subject_ids)


def sync_all_teachers_for_tenant(tenant) -> None:
    for teacher_id in (
        TeachingAssignment.objects.filter(tenant=tenant, is_deleted=False)
        .values_list("teacher_id", flat=True)
        .distinct()
    ):
        teacher = Teacher.objects.filter(pk=teacher_id).first()
        if teacher is not None:
            sync_teacher_subjects_from_assignments(teacher)