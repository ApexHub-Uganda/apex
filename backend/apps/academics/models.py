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
    term_number = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1, 2, or 3 for Kenyan terms")
    start_date = models.DateField()
    end_date = models.DateField()
    reporting_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    mid_term_break_start = models.DateField(null=True, blank=True)
    mid_term_break_end = models.DateField(null=True, blank=True)
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
    level_type = models.CharField(
        max_length=30,
        choices=[
            ("pre_primary", "Pre-Primary"),
            ("primary", "Primary"),
            ("junior_secondary", "Junior Secondary"),
            ("senior_secondary", "Senior Secondary"),
            ("tertiary", "Tertiary"),
        ],
        blank=True,
    )
    curriculum = models.CharField(
        max_length=20,
        choices=[
            ("cbc", "CBC"),
            ("844", "8-4-4"),
            ("igcse", "IGCSE"),
            ("other", "Other"),
        ],
        default="cbc",
    )
    section = models.CharField(max_length=20, blank=True, help_text="Section label e.g. A, B, East")
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

    @property
    def has_papers(self) -> bool:
        return self.papers.exists()


class SubjectPaper(BaseModel):
    """Optional exam papers within a subject (e.g. Mathematics M223, M224)."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="papers")
    code = models.CharField(max_length=20, help_text="Paper code e.g. M223")
    name = models.CharField(max_length=100, blank=True, help_text="Optional label e.g. Paper 1")
    sort_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["sort_order", "code"]
        unique_together = [("tenant", "subject", "code")]
        verbose_name = "subject paper"


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


class Period(BaseModel):
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_break = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "start_time"]
        unique_together = [("tenant", "name")]


class Classroom(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveIntegerField(default=40)
    room_type = models.CharField(
        max_length=20,
        choices=[
            ("classroom", "Classroom"),
            ("lab", "Laboratory"),
            ("hall", "Hall"),
            ("office", "Office"),
            ("other", "Other"),
        ],
        default="classroom",
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "code")]


class ClassNotice(BaseModel):
    """Notices published to a specific class (class teacher tools)."""

    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_notices",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["tenant", "school_class", "is_published"])]


class DisciplineRemark(BaseModel):
    """Student discipline or welfare remarks."""

    REMARK_TYPES = [
        ("commendation", "Commendation"),
        ("warning", "Warning"),
        ("sanction", "Sanction"),
    ]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="discipline_remarks")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="discipline_remarks")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )
    remark_type = models.CharField(max_length=20, choices=REMARK_TYPES, default="warning")
    title = models.CharField(max_length=255)
    description = models.TextField()
    incident_date = models.DateField()
    recorded_by = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )

    class Meta:
        ordering = ["-incident_date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "school_class", "incident_date"]),
            models.Index(fields=["tenant", "student"]),
        ]