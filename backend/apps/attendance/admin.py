from django.contrib import admin
from apps.attendance.models import AttendanceRecord
@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["date", "attendee_type", "student", "staff", "status"]
