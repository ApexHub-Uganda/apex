from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.students.views import AdmissionViewSet, GuardianViewSet, MedicalRecordViewSet, ParentViewSet, StudentViewSet

router = DefaultRouter()
router.register("parents", ParentViewSet, basename="parent")
router.register("", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("admissions", AdmissionViewSet, basename="admission")
router.register("medical-records", MedicalRecordViewSet, basename="medical-record")

urlpatterns = [path("", include(router.urls))]