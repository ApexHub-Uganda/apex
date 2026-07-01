from django.contrib import admin

from apps.academics.models import AcademicYear, Assignment, Class, Department, Homework, Stream, Subject, Term, Timetable

for model in [AcademicYear, Term, Department, Class, Stream, Subject, Timetable, Assignment, Homework]:
    admin.site.register(model)