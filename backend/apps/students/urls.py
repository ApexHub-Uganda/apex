from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.students.parent_portal_views import (
    ParentPortalAcademicsView,
    ParentPortalFinanceView,
    ParentPortalOverviewView,
)
from apps.students.views import AdmissionViewSet, GuardianViewSet, MedicalRecordViewSet, ParentViewSet, StudentViewSet

router = DefaultRouter()
router.register("parents", ParentViewSet, basename="parent")
router.register("", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("admissions", AdmissionViewSet, basename="admission")
router.register("medical-records", MedicalRecordViewSet, basename="medical-record")

urlpatterns = [
    path("portal/overview/", ParentPortalOverviewView.as_view(), name="parent-portal-overview"),
    path("portal/finance/", ParentPortalFinanceView.as_view(), name="parent-portal-finance"),
    path("portal/academics/", ParentPortalAcademicsView.as_view(), name="parent-portal-academics"),
    path("", include(router.urls)),
]