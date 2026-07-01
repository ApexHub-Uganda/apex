from django.contrib import admin

from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["admission_number", "first_name", "last_name", "school_class", "status", "tenant"]
    list_filter = ["status", "gender"]
    search_fields = ["admission_number", "first_name", "last_name"]


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "email", "phone", "tenant"]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "student", "relationship", "is_primary"]


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ["student", "application_date", "status", "grade_applied"]


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "condition", "is_chronic", "recorded_date"]