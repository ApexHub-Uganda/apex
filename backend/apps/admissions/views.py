from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Class
from apps.admissions.models import AdmissionApplication, AdmissionVacancy
from apps.admissions.serializers import (
    AdmitApplicationSerializer,
    AdmissionApplicationSerializer,
    AdmissionVacancySerializer,
    PublicAdmissionVacancySerializer,
)
from apps.admissions.services import admit_application, reject_application
from apps.core.constants import UserRole
from apps.core.permissions import IsSchoolPortalUser, IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet


class AdmissionVacancyViewSet(BaseModelViewSet):
    required_feature_key = "admission_vacancies"
    queryset = AdmissionVacancy.objects.select_related("school_class", "academic_year")
    serializer_class = AdmissionVacancySerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["is_active", "is_published", "show_on_landing", "show_on_parent_portal"]
    search_fields = ["title", "grade_levels", "description"]

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        vacancy = self.get_object()
        vacancy.is_published = True
        vacancy.is_active = True
        vacancy.updated_by = request.user
        vacancy.save(update_fields=["is_published", "is_active", "updated_by", "updated_at"])
        return Response(
            {"success": True, "message": "Vacancy published.", "data": self.get_serializer(vacancy).data},
        )


class AdmissionApplicationViewSet(BaseModelViewSet):
    required_feature_key = "admissions"
    queryset = AdmissionApplication.objects.select_related(
        "student", "vacancy", "admitted_class",
    )
    serializer_class = AdmissionApplicationSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "vacancy", "grade_applied"]
    search_fields = ["first_name", "last_name", "parent_name", "parent_email", "grade_applied"]

    def get_queryset(self):
        qs = super().get_queryset()
        admitted_only = self.request.query_params.get("admitted_only")
        if admitted_only and str(admitted_only).lower() in ("1", "true", "yes"):
            return qs.filter(status="admitted")
        exclude_admitted = self.request.query_params.get("exclude_admitted")
        if exclude_admitted and str(exclude_admitted).lower() in ("1", "true", "yes"):
            return qs.exclude(status="admitted")
        return qs

    @action(detail=True, methods=["post"])
    def admit(self, request, pk=None):
        application = self.get_object()
        if application.status == "admitted":
            return Response(
                {"success": False, "message": "Application is already admitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = AdmitApplicationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        school_class = None
        class_id = data.get("school_class")
        if class_id:
            school_class = Class.objects.filter(pk=class_id, tenant=application.tenant).first()
            if school_class is None:
                return Response(
                    {"success": False, "message": "Invalid class for this school."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            student = admit_application(
                application,
                school_class=school_class,
                admission_number=(data.get("admission_number") or "").strip() or None,
                user=request.user,
            )
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        application.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Applicant admitted as {student.admission_number}.",
            "data": self.get_serializer(application).data,
        })

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        application = self.get_object()
        if application.status == "admitted":
            return Response(
                {"success": False, "message": "Cannot reject an admitted application."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get("reason") or "").strip()
        reject_application(application, reason=reason, user=request.user)
        return Response({
            "success": True,
            "message": "Application rejected.",
            "data": self.get_serializer(application).data,
        })


class AdmittedStudentViewSet(AdmissionApplicationViewSet):
    """Read-only list of admitted applications for the admitted_students feature."""

    required_feature_key = "admitted_students"
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return super().get_queryset().filter(status="admitted")


class PublicVacancyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import models as db_models

        today = timezone.now().date()
        qs = AdmissionVacancy.all_objects.filter(
            is_deleted=False,
            is_active=True,
            is_published=True,
            show_on_landing=True,
        ).select_related("tenant", "school_class").filter(
            Q(application_deadline__isnull=True) | Q(application_deadline__gte=today),
        ).annotate(
            remaining=db_models.F("openings_count") - db_models.F("filled_count"),
        ).filter(remaining__gt=0).order_by("-created_at")[:50]

        data = PublicAdmissionVacancySerializer(qs, many=True).data
        return Response({"success": True, "data": {"vacancies": data}})


class PortalVacancyListView(APIView):
    """Published vacancies for authenticated portal users (e.g. parent dashboards)."""

    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None or not tenant.has_feature("admission_vacancies"):
            return Response({"success": True, "data": {"vacancies": []}})
        from django.db import models as db_models

        today = timezone.now().date()
        qs = AdmissionVacancy.objects.filter(
            tenant=tenant,
            is_active=True,
            is_published=True,
            show_on_parent_portal=True,
        ).select_related("school_class").filter(
            Q(application_deadline__isnull=True) | Q(application_deadline__gte=today),
        ).annotate(
            remaining=db_models.F("openings_count") - db_models.F("filled_count"),
        ).filter(remaining__gt=0).order_by("-created_at")

        data = AdmissionVacancySerializer(qs, many=True).data
        return Response({"success": True, "data": {"vacancies": data}})