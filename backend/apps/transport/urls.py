from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.transport.views import VehicleViewSet, DriverViewSet, RouteViewSet, StudentTransportViewSet

router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("drivers", DriverViewSet, basename="driver")
router.register("routes", RouteViewSet, basename="route")
router.register("student-assignments", StudentTransportViewSet, basename="student-transport")

urlpatterns = [path("", include(router.urls))]
