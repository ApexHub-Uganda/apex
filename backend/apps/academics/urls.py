from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics.assignment_marks_views import (
    AssignmentGradeCalculationApplyView,
    AssignmentGradeCalculationOptionsView,
    AssignmentMarksBulkView,
    AssignmentMarksCreateView,
    AssignmentMarksOptionsView,
)
from apps.academics.timetable_generation_views import (
    TimetableDraftDetailView,
    TimetableGenerateView,
    TimetableGenerationContextView,
    TimetableScheduleViewSet,
)
from apps.academics.timetable_builder_views import (
    TimetableClassGridView,
    TimetableCreateDraftView,
    TimetableDefaultTeacherView,
    TimetablePeriodsSyncView,
    TimetablePrintPdfView,
    TimetablePublishView,
    TimetableUnpublishView,
    TimetableValidateGridView,
    TimetableWizardContextView,
)
from apps.academics.exam_timetable_views import (
    ExamTimetableContextView,
    ExamTimetableCreateDraftView,
    ExamTimetablePrintPdfView,
    ExamTimetablePublishView,
    ExamTimetableSlotsView,
    ExamTimetableValidateView,
)
from apps.academics.promotion_report_views import (
    ClassBroadsheetPdfView,
    PromotionCommitView,
    PromotionContextView,
    PromotionPreviewView,
    PromotionUndoView,
    ReportCardGenerateView,
    ReportCardListLatestView,
    ReportCardPdfView,
    ReportCardPublishView,
)
from apps.academics.dos_ops_views import (
    AcademicTranscriptPdfView,
    AssessmentSchemeViewSet,
    DosMarksCompletenessView,
    DosPerformanceView,
    DosReportStatusView,
    DosTeacherLoadView,
    LeavingCertificatePdfView,
    StudentSubjectRegistrationViewSet,
    SubjectCombinationViewSet,
    UnebCandidateExportView,
    UgandaSeedView,
)
from apps.academics.views import (
    AcademicWorkspaceView,
    AcademicYearViewSet,
    AssignmentViewSet,
    ClassNoticeViewSet,
    ClassViewSet,
    ClassroomViewSet,
    DepartmentViewSet,
    DisciplineRemarkViewSet,
    HomeworkViewSet,
    PeriodViewSet,
    StreamViewSet,
    SubjectPaperViewSet,
    SubjectViewSet,
    TeachingAssignmentViewSet,
    TermViewSet,
    TimetableViewSet,
)

router = DefaultRouter()
router.register("years", AcademicYearViewSet, basename="academic-year")
router.register("terms", TermViewSet, basename="term")
router.register("departments", DepartmentViewSet, basename="department")
router.register("classes", ClassViewSet, basename="class")
router.register("streams", StreamViewSet, basename="stream")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("subject-papers", SubjectPaperViewSet, basename="subject-paper")
router.register("timetables", TimetableViewSet, basename="timetable")
router.register("timetable-schedules", TimetableScheduleViewSet, basename="timetable-schedule")
router.register("teaching-assignments", TeachingAssignmentViewSet, basename="teaching-assignment")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("homework", HomeworkViewSet, basename="homework")
router.register("periods", PeriodViewSet, basename="period")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("class-notices", ClassNoticeViewSet, basename="class-notice")
router.register("discipline-remarks", DisciplineRemarkViewSet, basename="discipline-remark")
router.register("assessment-schemes", AssessmentSchemeViewSet, basename="assessment-scheme")
router.register("subject-combinations", SubjectCombinationViewSet, basename="subject-combination")
router.register("subject-registrations", StudentSubjectRegistrationViewSet, basename="subject-registration")

urlpatterns = [
    path("promotion/context/", PromotionContextView.as_view(), name="promotion-context"),
    path("promotion/preview/", PromotionPreviewView.as_view(), name="promotion-preview"),
    path("promotion/<uuid:batch_id>/commit/", PromotionCommitView.as_view(), name="promotion-commit"),
    path("promotion/<uuid:batch_id>/undo/", PromotionUndoView.as_view(), name="promotion-undo"),
    path("report-cards/generate/", ReportCardGenerateView.as_view(), name="report-cards-generate"),
    path("report-cards/publish/", ReportCardPublishView.as_view(), name="report-cards-publish"),
    path("report-cards/latest/", ReportCardListLatestView.as_view(), name="report-cards-latest"),
    path("report-cards/<uuid:pk>/pdf/", ReportCardPdfView.as_view(), name="report-card-pdf"),
    path("report-cards/broadsheet.pdf", ClassBroadsheetPdfView.as_view(), name="report-cards-broadsheet"),
    path("dos/performance/", DosPerformanceView.as_view(), name="dos-performance"),
    path("dos/marks-completeness/", DosMarksCompletenessView.as_view(), name="dos-marks-completeness"),
    path("dos/teacher-load/", DosTeacherLoadView.as_view(), name="dos-teacher-load"),
    path("dos/report-status/", DosReportStatusView.as_view(), name="dos-report-status"),
    path("dos/uneb-candidates.csv", UnebCandidateExportView.as_view(), name="dos-uneb-export"),
    path("uganda-seed/", UgandaSeedView.as_view(), name="uganda-seed"),
    path("certificates/<uuid:student_id>/leaving.pdf", LeavingCertificatePdfView.as_view(), name="leaving-certificate"),
    path("certificates/<uuid:student_id>/transcript.pdf", AcademicTranscriptPdfView.as_view(), name="academic-transcript"),
    path("workspace/", AcademicWorkspaceView.as_view(), name="academic-workspace"),
    path("assignment-marks/options/", AssignmentMarksOptionsView.as_view(), name="assignment-marks-options"),
    path("assignment-marks/create/", AssignmentMarksCreateView.as_view(), name="assignment-marks-create"),
    path("assignment-marks/bulk/", AssignmentMarksBulkView.as_view(), name="assignment-marks-bulk"),
    path("assignment-grades/options/", AssignmentGradeCalculationOptionsView.as_view(), name="assignment-grades-options"),
    path("assignment-grades/apply/", AssignmentGradeCalculationApplyView.as_view(), name="assignment-grades-apply"),
    path("timetables/generate/context/", TimetableGenerationContextView.as_view(), name="timetable-generate-context"),
    path("timetables/generate/", TimetableGenerateView.as_view(), name="timetable-generate"),
    path("timetables/generate/<uuid:draft_id>/", TimetableDraftDetailView.as_view(), name="timetable-draft"),
    # Class-by-class grid builder + print
    path("timetables/wizard/context/", TimetableWizardContextView.as_view(), name="timetable-wizard-context"),
    path("timetables/wizard/periods/", TimetablePeriodsSyncView.as_view(), name="timetable-wizard-periods"),
    path("timetables/wizard/grid/", TimetableClassGridView.as_view(), name="timetable-wizard-grid"),
    path("timetables/wizard/validate/", TimetableValidateGridView.as_view(), name="timetable-wizard-validate"),
    path("timetables/wizard/default-teacher/", TimetableDefaultTeacherView.as_view(), name="timetable-wizard-default-teacher"),
    path("timetables/wizard/publish/", TimetablePublishView.as_view(), name="timetable-publish"),
    path("timetables/wizard/unpublish/", TimetableUnpublishView.as_view(), name="timetable-unpublish"),
    path("timetables/wizard/create-draft/", TimetableCreateDraftView.as_view(), name="timetable-create-draft"),
    path("timetables/print.pdf", TimetablePrintPdfView.as_view(), name="timetable-print-pdf"),
    # Examination timetable (date + time, free invigilator pick)
    path("timetables/exam/context/", ExamTimetableContextView.as_view(), name="exam-timetable-context"),
    path("timetables/exam/create-draft/", ExamTimetableCreateDraftView.as_view(), name="exam-timetable-create-draft"),
    path("timetables/exam/slots/", ExamTimetableSlotsView.as_view(), name="exam-timetable-slots"),
    path("timetables/exam/validate/", ExamTimetableValidateView.as_view(), name="exam-timetable-validate"),
    path("timetables/exam/publish/", ExamTimetablePublishView.as_view(), name="exam-timetable-publish"),
    path("timetables/exam/print.pdf", ExamTimetablePrintPdfView.as_view(), name="exam-timetable-print-pdf"),
    path("", include(router.urls)),
]
