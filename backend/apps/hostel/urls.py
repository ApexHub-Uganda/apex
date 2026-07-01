from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hostel.views import HostelViewSet, RoomViewSet, AllocationViewSet

router = DefaultRouter()
router.register("", HostelViewSet, basename="hostel")
router.register("rooms", RoomViewSet, basename="room")
router.register("allocations", AllocationViewSet, basename="allocation")

urlpatterns = [path("", include(router.urls))]
