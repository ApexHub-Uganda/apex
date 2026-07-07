from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.examinations.views import (
    ExamViewSet,
    ExaminationReferenceView,
    ExaminationSessionViewSet,
    GradeViewSet,
    GradingScaleViewSet,
    MarksApprovalQueueView,
    MarksEntryBulkView,
    MarksEntryOptionsView,
    ReportCardViewSet,
    WorkflowBulkActionView,
)

router = DefaultRouter()
router.register("grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register("sessions", ExaminationSessionViewSet, basename="examination-session")
router.register("exams", ExamViewSet, basename="exam")
router.register("grades", GradeViewSet, basename="grade")
router.register("report-cards", ReportCardViewSet, basename="report-card")

urlpatterns = [
    path("reference/", ExaminationReferenceView.as_view(), name="examination-reference"),
    path("marks-entry/options/", MarksEntryOptionsView.as_view(), name="marks-entry-options"),
    path("marks-entry/bulk/", MarksEntryBulkView.as_view(), name="marks-entry-bulk"),
    path("marks-approval/queue/", MarksApprovalQueueView.as_view(), name="marks-approval-queue"),
    path("workflow/bulk/", WorkflowBulkActionView.as_view(), name="workflow-bulk"),
    path("", include(router.urls)),
]
