from django.urls import include, path
from rest_framework.routers import DefaultRouter

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
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("homework", HomeworkViewSet, basename="homework")
router.register("periods", PeriodViewSet, basename="period")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("class-notices", ClassNoticeViewSet, basename="class-notice")
router.register("discipline-remarks", DisciplineRemarkViewSet, basename="discipline-remark")

urlpatterns = [
    path("workspace/", AcademicWorkspaceView.as_view(), name="academic-workspace"),
    path("", include(router.urls)),
]