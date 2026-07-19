"""Examination models."""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.examinations.constants import (
    EXAM_LIFECYCLE_CHOICES,
    EXAM_LIFECYCLE_DRAFT,
    EXAMINATION_SESSION_STATUS_CHOICES,
    EXAMINATION_SESSION_PLANNED,
    GRADE_ENTRY_STATUS_CHOICES,
    MARKS_STATUS_CHOICES,
    MARKS_STATUS_DRAFT,
)


class GradingScheme(BaseModel):
    """Named grading scheme — a set of score bands mapped to letter grades."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "name")]
        verbose_name = "grading scheme"

    def __str__(self) -> str:
        return self.name


class GradingSchemeBand(BaseModel):
    """One score range within a grading scheme."""

    scheme = models.ForeignKey(
        GradingScheme,
        on_delete=models.CASCADE,
        related_name="bands",
    )
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    remarks = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-min_score"]
        verbose_name = "grading scheme band"

    def __str__(self) -> str:
        return f"{self.grade} ({self.min_score}–{self.max_score})"


class GradingScale(BaseModel):
    """Legacy flat grading rows — superseded by GradingScheme + GradingSchemeBand."""

    name = models.CharField(max_length=100)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    remarks = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-min_score"]


class ExaminationSession(BaseModel):
    """School-wide examination window (e.g. end-of-term series)."""

    name = models.CharField(max_length=255)
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.CASCADE,
        related_name="examination_sessions",
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examination_sessions",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=EXAMINATION_SESSION_STATUS_CHOICES,
        default=EXAMINATION_SESSION_PLANNED,
        db_index=True,
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["tenant", "academic_year", "status"])]


class Exam(BaseModel):
    name = models.CharField(max_length=255)
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, related_name="exams")
    paper = models.ForeignKey(
        "academics.SubjectPaper",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
        help_text="Optional paper when the subject has multiple papers",
    )
    school_class = models.ForeignKey("academics.Class", on_delete=models.CASCADE, related_name="exams")
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="exams",
        null=True,
        blank=True,
        help_text="Optional for class assignments tracked outside term examinations",
    )
    examination_session = models.ForeignKey(
        ExaminationSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
    )
    exam_date = models.DateField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    exam_type = models.CharField(
        max_length=20,
        choices=[
            ("midterm", "Midterm"),
            ("final", "Final"),
            ("continuous", "Continuous Assessment"),
            ("assignment", "Class Assignment"),
        ],
        default="final",
    )
    lifecycle_status = models.CharField(
        max_length=20,
        choices=EXAM_LIFECYCLE_CHOICES,
        default=EXAM_LIFECYCLE_DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_exams",
    )
    marks_status = models.CharField(
        max_length=20,
        choices=MARKS_STATUS_CHOICES,
        default=MARKS_STATUS_DRAFT,
        db_index=True,
    )
    marks_submitted_at = models.DateTimeField(null=True, blank=True)
    marks_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_submitted_exams",
    )
    marks_approved_at = models.DateTimeField(null=True, blank=True)
    marks_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_approved_exams",
    )
    marks_locked_at = models.DateTimeField(null=True, blank=True)
    marks_locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_locked_exams",
    )
    marks_reopened_at = models.DateTimeField(null=True, blank=True)
    marks_reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_reopened_exams",
    )
    marks_reopen_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-exam_date"]
        indexes = [
            models.Index(fields=["tenant", "school_class", "term"]),
            models.Index(fields=["tenant", "lifecycle_status", "marks_status"]),
        ]

class Grade(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True)
    remarks = models.TextField(blank=True)
    entry_status = models.CharField(
        max_length=20,
        choices=GRADE_ENTRY_STATUS_CHOICES,
        default=MARKS_STATUS_DRAFT,
        db_index=True,
    )
    graded_by = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="graded_entries")

    class Meta:
        unique_together = [("tenant", "exam", "student")]
        ordering = ["-score"]


class ReportCard(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_cards")
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="report_cards")
    school_class = models.ForeignKey("academics.Class", on_delete=models.CASCADE, related_name="report_cards")
    stream = models.ForeignKey(
        "academics.Stream", on_delete=models.SET_NULL, null=True, blank=True, related_name="report_cards",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear", on_delete=models.SET_NULL, null=True, blank=True, related_name="report_cards",
    )
    version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True, db_index=True)
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    stream_rank = models.PositiveIntegerField(null=True, blank=True)
    class_size = models.PositiveIntegerField(null=True, blank=True)
    stream_size = models.PositiveIntegerField(null=True, blank=True)
    aggregate_points = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    division = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)
    teacher_remarks = models.TextField(blank=True)
    principal_remarks = models.TextField(blank=True)
    dos_remarks = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_report_cards",
    )
    days_present = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    days_late = models.PositiveIntegerField(default=0)
    days_excused = models.PositiveIntegerField(default=0)
    next_term_opens = models.DateField(null=True, blank=True)
    generation_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-term__start_date", "-version"]
        indexes = [
            models.Index(fields=["tenant", "term", "school_class", "is_latest"]),
            models.Index(fields=["tenant", "student", "term", "is_latest"]),
            models.Index(fields=["tenant", "is_published", "is_latest"]),
        ]


class ReportCardSubjectLine(BaseModel):
    """Per-subject breakdown line on a generated report card."""

    report_card = models.ForeignKey(ReportCard, on_delete=models.CASCADE, related_name="subject_lines")
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.SET_NULL, null=True, blank=True, related_name="report_card_lines",
    )
    subject_name = models.CharField(max_length=120)
    subject_code = models.CharField(max_length=30, blank=True)
    paper_breakdown = models.JSONField(default=list, blank=True)
    ca_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    exam_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    grade = models.CharField(max_length=10, blank=True)
    grade_point = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    remarks = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["sort_order", "subject_name"]
