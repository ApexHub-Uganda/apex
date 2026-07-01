from django.contrib import admin
from apps.staff.models import Staff, Teacher
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ["employee_id", "first_name", "last_name", "designation", "status"]
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ["staff", "qualification", "is_class_teacher"]
