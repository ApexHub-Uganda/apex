from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.staff.models import Staff, Teacher
from apps.staff.serializers import (
    StaffDetailSerializer,
    StaffListSerializer,
    StaffOnboardResponseSerializer,
    StaffOnboardSerializer,
    StaffUpdateSerializer,
    TeacherSerializer,
    serialize_role_options,
)
from apps.staff.staff_roles import get_role_definition


class StaffViewSet(BaseModelViewSet):
    required_feature_key = "staff_management"
    queryset = Staff.objects.select_related("department", "user", "supervisor").prefetch_related(
        "teacher_profile", "teacher_profile__subjects",
    )
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "department", "employment_type", "staff_category", "portal_role"]
    search_fields = [
        "first_name", "last_name", "middle_name", "employee_id",
        "email", "personal_email", "designation", "national_id",
    ]

    def get_serializer_class(self):
        if self.action == "create":
            return StaffOnboardSerializer
        if self.action in ("update", "partial_update"):
            return StaffUpdateSerializer
        if self.action == "retrieve":
            return StaffDetailSerializer
        return StaffListSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        output = StaffOnboardResponseSerializer(staff, context=self.get_serializer_context())
        message = "Staff member added successfully."
        temp = getattr(staff, "_onboarding_temp_password", None)
        if temp and staff.has_portal_access:
            message += " A portal account was created — share the temporary password securely."
        return Response({
            "success": True,
            "message": message,
            "data": output.data,
            "temporary_password": temp,
        }, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = StaffDetailSerializer(instance, context=self.get_serializer_context())
        return Response({"success": True, "data": serializer.data})

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = StaffListSerializer(page or queryset, many=True, context=self.get_serializer_context())
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="role-options")
    def role_options(self, request: Request) -> Response:
        return Response({
            "success": True,
            "data": serialize_role_options(),
        })

    @action(detail=False, methods=["get"], url_path="role-preview")
    def role_preview(self, request: Request) -> Response:
        role = request.query_params.get("role", "")
        return Response({
            "success": True,
            "data": get_role_definition(role),
        })


class TeacherViewSet(BaseModelViewSet):
    required_feature_key = "staff_management"
    queryset = Teacher.objects.select_related("staff").prefetch_related("subjects")
    serializer_class = TeacherSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["is_class_teacher"]
    search_fields = ["staff__first_name", "staff__last_name"]