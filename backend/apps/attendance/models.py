"""Attendance models."""
from django.db import models

from apps.core.models import BaseModel


class AttendanceRecord(BaseModel):
    ATTENDEE_TYPES = [("student", "Student"), ("staff", "Staff")]
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("excused", "Excused"),
        ("half_day", "Half Day"),
    ]

    attendee_type = models.CharField(max_length=10, choices=ATTENDEE_TYPES, db_index=True)
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, null=True, blank=True, related_name="attendance_records")
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, null=True, blank=True, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="marked_attendance")
    # Optional GPS capture (staff self check-in / geo-verified marking)
    check_in_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    check_out_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_out_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_out_accuracy_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["tenant", "date", "attendee_type"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(attendee_type="student", student_id__isnull=False)
                    | models.Q(attendee_type="staff", staff_id__isnull=False)
                ),
                name="attendance_has_attendee",
            ),
        ]


class SchoolGeofence(BaseModel):
    """
    Campus perimeter polygon for GPS-based staff attendance.

    Vertices are WGS84 points [{lat, lng, accuracy_m?, label?}]. Minimum 4 corners.
    """

    name = models.CharField(max_length=100, default="Main campus")
    vertices = models.JSONField(
        default=list,
        help_text="List of {lat, lng, accuracy_m} corner points (min 4).",
    )
    buffer_meters = models.PositiveIntegerField(
        default=25,
        help_text="Extra allowance outside the polygon edge (GPS drift).",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="When true, staff check-in and class marking require being on campus.",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "school geofence"
        verbose_name_plural = "school geofences"

    def __str__(self) -> str:
        return f"{self.name} ({len(self.vertices or [])} pts)"


class LessonAttendanceSession(BaseModel):
    """Per-lesson attendance session tied to a class and subject."""

    SESSION_OPEN = "open"
    SESSION_CLOSED = "closed"
    STATUS_CHOICES = [
        (SESSION_OPEN, "Open"),
        (SESSION_CLOSED, "Closed"),
    ]

    school_class = models.ForeignKey(
        "academics.Class",
        on_delete=models.CASCADE,
        related_name="lesson_attendance_sessions",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="lesson_attendance_sessions",
    )
    teacher = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        related_name="lesson_attendance_sessions",
    )
    timetable = models.ForeignKey(
        "academics.Timetable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_attendance_sessions",
    )
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SESSION_OPEN, db_index=True)
    topic = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "school_class", "date"]),
            models.Index(fields=["tenant", "teacher", "date"]),
        ]


class LessonAttendanceEntry(BaseModel):
    """Student attendance row within a lesson session."""

    session = models.ForeignKey(
        LessonAttendanceSession,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="lesson_attendance_entries",
    )
    status = models.CharField(max_length=10, choices=AttendanceRecord.STATUS_CHOICES, default="present")
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "session", "student")]
        ordering = ["student__last_name", "student__first_name"]
        indexes = [models.Index(fields=["tenant", "session", "status"])]