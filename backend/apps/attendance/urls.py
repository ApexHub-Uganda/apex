from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.attendance.views import AttendanceRecordViewSet

router = DefaultRouter()
router.register("", AttendanceRecordViewSet, basename="attendance")

urlpatterns = [path("", include(router.urls))]
