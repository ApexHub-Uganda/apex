"""Admission workflow helpers."""
from __future__ import annotations

from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.admissions.models import AdmissionApplication, AdmissionVacancy
from apps.students.models import Student


def _next_admission_number(tenant) -> str:
    code = (tenant.code or "SCH").upper()
    count = Student.all_objects.filter(tenant=tenant, is_deleted=False).count() + 1
    candidate = f"{code}-{count:04d}"
    while Student.all_objects.filter(tenant=tenant, admission_number=candidate).exists():
        count += 1
        candidate = f"{code}-{count:04d}"
    return candidate


@transaction.atomic
def admit_application(
    application: AdmissionApplication,
    *,
    school_class=None,
    admission_number: Optional[str] = None,
    user: Any = None,
) -> Student:
    if application.status == "admitted" and application.student_id:
        return application.student

    tenant = application.tenant
    if tenant is None:
        raise ValueError("Application has no tenant.")

    if admission_number:
        if Student.all_objects.filter(tenant=tenant, admission_number=admission_number).exists():
            raise ValueError(f"Admission number '{admission_number}' already exists.")
    else:
        admission_number = _next_admission_number(tenant)

    resolved_class = school_class or application.admitted_class
    if resolved_class is None and application.vacancy and application.vacancy.school_class_id:
        resolved_class = application.vacancy.school_class

    today = timezone.now().date()
    student = Student.all_objects.create(
        tenant=tenant,
        admission_number=admission_number,
        first_name=application.first_name,
        middle_name=application.middle_name,
        last_name=application.last_name,
        date_of_birth=application.date_of_birth,
        gender=application.gender,
        email=application.email,
        phone=application.phone,
        address=application.address,
        previous_school=application.previous_school,
        school_class=resolved_class,
        enrollment_date=today,
        status="active",
        created_by=user,
        updated_by=user,
    )

    application.student = student
    application.status = "admitted"
    application.admission_date = today
    application.admitted_class = resolved_class
    if user:
        application.updated_by = user
    application.save(
        update_fields=[
            "student",
            "status",
            "admission_date",
            "admitted_class",
            "updated_by",
            "updated_at",
        ],
    )

    if application.vacancy_id:
        vacancy = AdmissionVacancy.objects.select_for_update().get(pk=application.vacancy_id)
        vacancy.filled_count = min(vacancy.openings_count, vacancy.filled_count + 1)
        if user:
            vacancy.updated_by = user
        vacancy.save(update_fields=["filled_count", "updated_by", "updated_at"])

    return student


def reject_application(application: AdmissionApplication, *, reason: str = "", user: Any = None) -> None:
    application.status = "rejected"
    if reason:
        application.notes = f"{application.notes}\n\nRejection: {reason}".strip()
    if user:
        application.updated_by = user
    application.save(update_fields=["status", "notes", "updated_by", "updated_at"])