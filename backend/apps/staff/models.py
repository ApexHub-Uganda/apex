"""Staff management models."""
from __future__ import annotations

from django.db import models

from apps.core.constants import UserRole
from apps.core.models import BaseModel
from apps.staff.staff_roles import STAFF_CATEGORY_CHOICES


class Staff(BaseModel):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
    )
    employee_id = models.CharField(max_length=50, db_index=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(help_text="Primary work email — used for portal login when enabled")
    personal_email = models.EmailField(blank=True, help_text="Personal / alternate email")
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        blank=True,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True, db_index=True)
    nationality = models.CharField(max_length=100, default="Kenyan")

    staff_category = models.CharField(max_length=20, choices=STAFF_CATEGORY_CHOICES, default="administrative")
    portal_role = models.CharField(
        max_length=30,
        choices=UserRole.CHOICES,
        default=UserRole.TEACHER,
        db_index=True,
        help_text="Dashboard role assigned when portal access is enabled",
    )
    department = models.ForeignKey(
        "academics.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
    )
    designation = models.CharField(max_length=100)
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    date_joined = models.DateField()
    date_left = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=[
            ("full_time", "Full Time"),
            ("part_time", "Part Time"),
            ("contract", "Contract"),
            ("intern", "Intern"),
        ],
        default="full_time",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("on_leave", "On Leave"),
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
        ],
        default="active",
    )
    has_portal_access = models.BooleanField(default=True)
    photo = models.ImageField(upload_to="staff/", blank=True, null=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    emergency_relationship = models.CharField(max_length=50, blank=True)
    qualification_summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "employee_id")]
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "portal_role"]),
            models.Index(fields=["tenant", "email"]),
        ]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()


class Teacher(BaseModel):
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name="teacher_profile")
    subjects = models.ManyToManyField("academics.Subject", related_name="teachers", blank=True)
    qualification = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    is_class_teacher = models.BooleanField(default=False)

    class Meta:
        ordering = ["staff__last_name"]