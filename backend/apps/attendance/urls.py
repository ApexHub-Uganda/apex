from django.urls import include, path
from rest_framework.routers import DefaultRouter

from django.urls import path

from apps.attendance.views import (
    AttendanceRecordViewSet,
    LessonAttendanceBulkView,
    LessonAttendanceEntryViewSet,
    LessonAttendanceSessionViewSet,
)

router = DefaultRouter()
router.register("", AttendanceRecordViewSet, basename="attendance")
router.register("lesson-sessions", LessonAttendanceSessionViewSet, basename="lesson-attendance-session")
router.register("lesson-entries", LessonAttendanceEntryViewSet, basename="lesson-attendance-entry")

urlpatterns = [
    path("lesson-sessions/bulk/", LessonAttendanceBulkView.as_view(), name="lesson-attendance-bulk"),
    path("", include(router.urls)),
]
