"""Student management models."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Parent(BaseModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="parent_profile", null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    occupation = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [models.Index(fields=["tenant", "email"])]


class Guardian(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="guardians")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "last_name"]


class Student(BaseModel):
    user = models.OneToOneField("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profile")
    admission_number = models.CharField(max_length=50, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female"), ("other", "Other")])
    photo = models.ImageField(upload_to="students/", blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    nationality = models.CharField(max_length=100, default="Kenyan")

    school_class = models.ForeignKey("academics.Class", on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    stream = models.ForeignKey("academics.Stream", on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    parents = models.ManyToManyField(Parent, related_name="children", blank=True)

    enrollment_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ("active", "Active"), ("graduated", "Graduated"),
        ("transferred", "Transferred"), ("suspended", "Suspended"), ("withdrawn", "Withdrawn"),
    ], default="active", db_index=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        unique_together = [("tenant", "admission_number")]
        indexes = [models.Index(fields=["tenant", "status"]), models.Index(fields=["tenant", "school_class"])]


class Admission(BaseModel):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="admission")
    application_date = models.DateField()
    admission_date = models.DateField(null=True, blank=True)
    previous_school = models.CharField(max_length=255, blank=True)
    grade_applied = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("waitlisted", "Waitlisted"),
    ], default="pending")
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