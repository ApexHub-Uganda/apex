"""Student management models."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Parent(BaseModel):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profile",
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(help_text="Primary contact email")
    alternate_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        blank=True,
    )
    national_id = models.CharField(max_length=50, blank=True)
    county = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    mpesa_phone = models.CharField(max_length=20, blank=True, help_text="M-Pesa number for fee payments")
    is_fee_payer = models.BooleanField(default=False)
    consent_for_sms = models.BooleanField(default=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=150, blank=True)
    relationship_to_student = models.CharField(
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
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Uganda")
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ("email", "Email"),
            ("phone", "Phone"),
            ("sms", "SMS"),
            ("whatsapp", "WhatsApp"),
        ],
        default="email",
    )
    is_emergency_contact = models.BooleanField(default=True)
    has_portal_access = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["tenant", "email"]),
            models.Index(fields=["tenant", "phone"]),
        ]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()


class Guardian(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="guardians")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    alternate_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    is_emergency_contact = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "last_name"]


class Student(BaseModel):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
    )
    admission_number = models.CharField(max_length=50, db_index=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
    )
    photo = models.ImageField(upload_to="students/", blank=True, null=True)
    email = models.EmailField(blank=True, help_text="Student email or parent-monitored address")
    alternate_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    nationality = models.CharField(max_length=100, default="Ugandan")
    religion = models.CharField(max_length=50, blank=True)
    place_of_birth = models.CharField(max_length=150, blank=True)
    previous_school = models.CharField(max_length=255, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    upi_number = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="Legacy national learner ID (e.g. former NEMIS UPI). Prefer registration_number.",
    )
    registration_number = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="School/national registration or index number (Uganda UNEB candidate no. when applicable).",
    )
    district = models.CharField(max_length=100, blank=True, help_text="Home district")
    house = models.CharField(max_length=50, blank=True, help_text="Sports/discipline house")
    birth_certificate_number = models.CharField(max_length=50, blank=True)
    county = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    curriculum_pathway = models.CharField(
        max_length=30,
        choices=[
            ("uneb", "UNEB (Uganda)"),
            ("uganda_cbe", "Uganda Competence-Based"),
            ("cbc", "CBC (Kenya)"),
            ("844", "8-4-4"),
            ("igcse", "IGCSE"),
            ("ace", "ACE"),
            ("other", "Other"),
        ],
        default="uneb",
        blank=True,
    )
    boarding_status = models.CharField(
        max_length=20,
        choices=[
            ("day", "Day Scholar"),
            ("boarding", "Boarding"),
            ("weekly", "Weekly Boarding"),
        ],
        default="day",
    )
    special_needs = models.BooleanField(default=False)
    special_needs_details = models.TextField(blank=True)

    school_class = models.ForeignKey(
        "academics.Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    stream = models.ForeignKey(
        "academics.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    parents = models.ManyToManyField(Parent, related_name="children", blank=True)

    enrollment_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("graduated", "Graduated"),
            ("transferred", "Transferred"),
            ("suspended", "Suspended"),
            ("withdrawn", "Withdrawn"),
        ],
        default="active",
        db_index=True,
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        unique_together = [("tenant", "admission_number")]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "school_class"]),
            models.Index(fields=["tenant", "email"]),
        ]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()


class Admission(BaseModel):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="admission")
    application_date = models.DateField()
    admission_date = models.DateField(null=True, blank=True)
    previous_school = models.CharField(max_length=255, blank=True)
    grade_applied = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("waitlisted", "Waitlisted"),
        ],
        default="pending",
    )
    notes = models.TextField(blank=True)
    documents = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-application_date"]


class MedicalRecord(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="medical_records")
    condition = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_chronic = models.BooleanField(default=False)
    medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    recorded_date = models.DateField()

    class Meta:
        ordering = ["-recorded_date"]