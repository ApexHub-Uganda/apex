from django.urls import include, path
from rest_framework.routers import DefaultRouter

from django.urls import path

from apps.attendance.class_attendance_views import (
    ClassAttendanceBulkView,
    ClassAttendanceOptionsView,
)
from apps.attendance.session_history_views import (
    AttendanceSessionDetailView,
    AttendanceSessionPdfView,
    AttendanceSessionsRecentView,
)
from apps.attendance.geofence_views import (
    LocationCheckView,
    SchoolGeofenceView,
    StaffAttendanceStatusView,
    StaffCheckInView,
    StaffCheckOutView,
)
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
    path("class-marking/options/", ClassAttendanceOptionsView.as_view(), name="class-attendance-options"),
    path("class-marking/bulk/", ClassAttendanceBulkView.as_view(), name="class-attendance-bulk"),
    path("lesson-sessions/bulk/", LessonAttendanceBulkView.as_view(), name="lesson-attendance-bulk"),
    path("sessions/recent/", AttendanceSessionsRecentView.as_view(), name="attendance-sessions-recent"),
    path("sessions/<path:session_key>/pdf/", AttendanceSessionPdfView.as_view(), name="attendance-session-pdf"),
    path("sessions/<path:session_key>/", AttendanceSessionDetailView.as_view(), name="attendance-session-detail"),
    path("geofence/", SchoolGeofenceView.as_view(), name="school-geofence"),
    path("location-check/", LocationCheckView.as_view(), name="location-check"),
    path("staff/status/", StaffAttendanceStatusView.as_view(), name="staff-attendance-status"),
    path("staff/check-in/", StaffCheckInView.as_view(), name="staff-check-in"),
    path("staff/check-out/", StaffCheckOutView.as_view(), name="staff-check-out"),
    path("", include(router.urls)),
]
