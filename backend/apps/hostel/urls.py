from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hostel.report_views import HostelReportsView
from apps.hostel.views import HostelViewSet, RoomViewSet, AllocationViewSet

router = DefaultRouter()
router.register("", HostelViewSet, basename="hostel")
router.register("rooms", RoomViewSet, basename="room")
router.register("allocations", AllocationViewSet, basename="allocation")

urlpatterns = [
    path("reports/", HostelReportsView.as_view(), name="hostel-reports"),
    path("", include(router.urls)),
]
