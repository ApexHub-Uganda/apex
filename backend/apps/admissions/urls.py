from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.admissions.views import (
    AdmittedStudentViewSet,
    AdmissionApplicationViewSet,
    AdmissionVacancyViewSet,
    PortalVacancyListView,
    PublicVacancyListView,
)

router = DefaultRouter()
router.register("applications", AdmissionApplicationViewSet, basename="admission-application")
router.register("admitted", AdmittedStudentViewSet, basename="admitted-student")
router.register("vacancies", AdmissionVacancyViewSet, basename="admission-vacancy")

urlpatterns = [
    path("public/vacancies/", PublicVacancyListView.as_view(), name="admission-public-vacancies"),
    path("portal/vacancies/", PortalVacancyListView.as_view(), name="admission-portal-vacancies"),
    path("", include(router.urls)),
]