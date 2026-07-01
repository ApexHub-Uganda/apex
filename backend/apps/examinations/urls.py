from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.examinations.views import GradingScaleViewSet, ExamViewSet, GradeViewSet, ReportCardViewSet

router = DefaultRouter()
router.register("grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register("exams", ExamViewSet, basename="exam")
router.register("grades", GradeViewSet, basename="grade")
router.register("report-cards", ReportCardViewSet, basename="report-card")

urlpatterns = [path("", include(router.urls))]
