from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.examinations.views import (
    ExamViewSet,
    ExaminationReferenceView,
    GradeViewSet,
    GradingScaleViewSet,
    MarksEntryBulkView,
    MarksEntryOptionsView,
    ReportCardViewSet,
)

router = DefaultRouter()
router.register("grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register("exams", ExamViewSet, basename="exam")
router.register("grades", GradeViewSet, basename="grade")
router.register("report-cards", ReportCardViewSet, basename="report-card")

urlpatterns = [
    path("reference/", ExaminationReferenceView.as_view(), name="examination-reference"),
    path("marks-entry/options/", MarksEntryOptionsView.as_view(), name="marks-entry-options"),
    path("marks-entry/bulk/", MarksEntryBulkView.as_view(), name="marks-entry-bulk"),
    path("", include(router.urls)),
]
