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

urlpatterns = [
    path("workspace/", AcademicWorkspaceView.as_view(), name="academic-workspace"),
    path("assignment-marks/options/", AssignmentMarksOptionsView.as_view(), name="assignment-marks-options"),
    path("assignment-marks/create/", AssignmentMarksCreateView.as_view(), name="assignment-marks-create"),
    path("assignment-marks/bulk/", AssignmentMarksBulkView.as_view(), name="assignment-marks-bulk"),
    path("assignment-grades/options/", AssignmentGradeCalculationOptionsView.as_view(), name="assignment-grades-options"),
    path("assignment-grades/apply/", AssignmentGradeCalculationApplyView.as_view(), name="assignment-grades-apply"),
    path("timetables/generate/context/", TimetableGenerationContextView.as_view(), name="timetable-generate-context"),
    path("timetables/generate/", TimetableGenerateView.as_view(), name="timetable-generate"),
    path("timetables/generate/<uuid:draft_id>/", TimetableDraftDetailView.as_view(), name="timetable-draft"),
    path("", include(router.urls)),
]