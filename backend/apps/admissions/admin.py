from django.contrib import admin

from apps.admissions.models import AdmissionApplication, AdmissionVacancy


@admin.register(AdmissionVacancy)
class AdmissionVacancyAdmin(admin.ModelAdmin):
    list_display = [
        "title", "grade_levels", "openings_count", "filled_count",
        "is_published", "show_on_landing", "show_on_parent_portal", "tenant",
    ]
    list_filter = ["is_active", "is_published", "show_on_landing", "show_on_parent_portal"]
    search_fields = ["title", "grade_levels"]


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "full_name", "grade_applied", "status", "application_date", "student", "tenant",
    ]
    list_filter = ["status", "grade_applied"]
    search_fields = ["first_name", "last_name", "parent_name", "parent_email"]