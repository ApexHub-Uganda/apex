from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hr.report_views import HRReportsView
from apps.hr.views import LeaveViewSet, PerformanceReviewViewSet

router = DefaultRouter()
router.register("leaves", LeaveViewSet, basename="leave")
router.register("performance-reviews", PerformanceReviewViewSet, basename="performance-review")

urlpatterns = [
    path("reports/", HRReportsView.as_view(), name="hr-reports"),
    path("", include(router.urls)),
]
