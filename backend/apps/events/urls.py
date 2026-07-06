from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.events.views import EventRegistrationViewSet, EventViewSet

router = DefaultRouter()
router.register("", EventViewSet, basename="event")
router.register("registrations", EventRegistrationViewSet, basename="event-registration")

urlpatterns = [path("", include(router.urls))]