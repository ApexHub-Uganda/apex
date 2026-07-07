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


class GradingScale(BaseModel):
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
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="exams")
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
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    teacher_remarks = models.TextField(blank=True)
    principal_remarks = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [("tenant", "student", "term")]
        ordering = ["-term__start_date"]