"""Admission applications and vacancy advertising."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class AdmissionVacancy(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    grade_levels = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated grade levels, e.g. Grade 1, Grade 2",
    )
    school_class = models.ForeignKey(
        "academics.Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_vacancies",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_vacancies",
    )
    openings_count = models.PositiveIntegerField(default=1)
    filled_count = models.PositiveIntegerField(default=0)
    application_deadline = models.DateField(null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    show_on_landing = models.BooleanField(default=False)
    show_on_parent_portal = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "admission vacancies"

    @property
    def remaining_openings(self) -> int:
        return max(0, self.openings_count - self.filled_count)

    @property
    def is_open(self) -> bool:
        if not self.is_active or not self.is_published:
            return False
        if self.remaining_openings <= 0:
            return False
        if self.application_deadline:
            from django.utils import timezone

            return self.application_deadline >= timezone.now().date()
        return True


class AdmissionApplication(BaseModel):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    parent_name = models.CharField(max_length=200)
    parent_email = models.EmailField(blank=True)
    parent_phone = models.CharField(max_length=20)
    parent_relationship = models.CharField(
        max_length=30,
        choices=[
            ("father", "Father"),
            ("mother", "Mother"),
            ("guardian", "Guardian"),
            ("sponsor", "Sponsor"),
            ("other", "Other"),
        ],
        default="guardian",
    )

    vacancy = models.ForeignKey(
        AdmissionVacancy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    grade_applied = models.CharField(max_length=50)
    previous_school = models.CharField(max_length=255, blank=True)
    application_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("waitlisted", "Waitlisted"),
            ("admitted", "Admitted"),
        ],
        default="pending",
        db_index=True,
    )
    notes = models.TextField(blank=True)
    documents = models.JSONField(default=list, blank=True)

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_applications",
    )
    admission_date = models.DateField(null=True, blank=True)
    admitted_class = models.ForeignKey(
        "academics.Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admitted_applications",
    )

    class Meta:
        ordering = ["-application_date", "-created_at"]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()