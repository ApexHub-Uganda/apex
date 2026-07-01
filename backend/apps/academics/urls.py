from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics.views import (
    AcademicYearViewSet, AssignmentViewSet, ClassViewSet, DepartmentViewSet,
    HomeworkViewSet, StreamViewSet, SubjectViewSet, TermViewSet, TimetableViewSet,
)

router = DefaultRouter()
router.register("years", AcademicYearViewSet, basename="academic-year")
router.register("terms", TermViewSet, basename="term")
router.register("departments", DepartmentViewSet, basename="department")
router.register("classes", ClassViewSet, basename="class")
router.register("streams", StreamViewSet, basename="stream")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("timetables", TimetableViewSet, basename="timetable")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("homework", HomeworkViewSet, basename="homework")

urlpatterns = [path("", include(router.urls))]