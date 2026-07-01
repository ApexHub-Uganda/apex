"""Academic structure models."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class AcademicYear(BaseModel):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("tenant", "name")]
        indexes = [models.Index(fields=["tenant", "is_current"])]


class Term(BaseModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_date"]
        unique_together = [("tenant", "academic_year", "name")]


class Department(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    head = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments")
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "code")]
        ordering = ["name"]


class Class(BaseModel):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")
    class_teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")
    capacity = models.PositiveIntegerField(default=40)
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "Classes"
        unique_together = [("tenant", "academic_year", "code")]
        ordering = ["name"]


class Stream(BaseModel):
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="streams")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        unique_together = [("tenant", "school_class", "name")]


class Subject(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="subjects")
    description = models.TextField(blank=True)
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        unique_together = [("tenant", "code")]
        ordering = ["name"]


class Timetable(BaseModel):
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="timetables")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="timetable_entries")
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="timetable_entries")
    day_of_week = models.PositiveSmallIntegerField(choices=[
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"),
        (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        indexes = [models.Index(fields=["tenant", "school_class", "day_of_week"])]


class Assignment(BaseModel):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assignments")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="assignments")
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="assignments")
    description = models.TextField()
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True)

    class Meta:
        ordering = ["-due_date"]


class Homework(BaseModel):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="homework")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="homework")
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="homework")
    description = models.TextField()
    assigned_date = models.DateField()
    due_date = models.DateField()
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_date"]