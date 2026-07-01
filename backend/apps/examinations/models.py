"""Examination models."""
from django.db import models
from apps.core.models import BaseModel

class GradingScale(BaseModel):
    name = models.CharField(max_length=100)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    remarks = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-min_score"]

class Exam(BaseModel):
    name = models.CharField(max_length=255)
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, related_name="exams")
    school_class = models.ForeignKey("academics.Class", on_delete=models.CASCADE, related_name="exams")
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="exams")
    exam_date = models.DateField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    exam_type = models.CharField(max_length=20, choices=[("midterm","Midterm"),("final","Final"),("continuous","Continuous Assessment")], default="final")

    class Meta:
        ordering = ["-exam_date"]

class Grade(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True)
    remarks = models.TextField(blank=True)
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
