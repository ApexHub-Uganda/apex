from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.staff.views import StaffViewSet, TeacherViewSet

router = DefaultRouter()
router.register("", StaffViewSet, basename="staff")
router.register("teachers", TeacherViewSet, basename="teacher")

urlpatterns = [path("", include(router.urls))]
