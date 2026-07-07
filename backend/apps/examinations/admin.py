from django.contrib import admin

from apps.examinations.models import Exam, ExaminationSession, Grade, GradingScale, ReportCard

admin.site.register(GradingScale)
admin.site.register(ExaminationSession)
admin.site.register(Exam)
admin.site.register(Grade)
admin.site.register(ReportCard)