from django.contrib import admin
from apps.attendance.models import AttendanceRecord, SchoolGeofence


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["date", "attendee_type", "student", "staff", "status"]


@admin.register(SchoolGeofence)
class SchoolGeofenceAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "is_enabled", "buffer_meters", "updated_at"]
    list_filter = ["is_enabled"]
