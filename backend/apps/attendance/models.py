"""Attendance models."""
from django.db import models
from apps.core.models import BaseModel

class AttendanceRecord(BaseModel):
    ATTENDEE_TYPES = [("student","Student"),("staff","Staff")]
    STATUS_CHOICES = [("present","Present"),("absent","Absent"),("late","Late"),("excused","Excused"),("half_day","Half Day")]

    attendee_type = models.CharField(max_length=10, choices=ATTENDEE_TYPES, db_index=True)
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, null=True, blank=True, related_name="attendance_records")
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, null=True, blank=True, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="marked_attendance")

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["tenant", "date", "attendee_type"])]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(attendee_type="student", student_id__isnull=False)
                    | models.Q(attendee_type="staff", staff_id__isnull=False)
                ),
                name="attendance_has_attendee",
            ),
        ]
