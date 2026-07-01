from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hr.views import LeaveViewSet, PerformanceReviewViewSet

router = DefaultRouter()
router.register("leaves", LeaveViewSet, basename="leave")
router.register("performance-reviews", PerformanceReviewViewSet, basename="performance-review")

urlpatterns = [path("", include(router.urls))]
