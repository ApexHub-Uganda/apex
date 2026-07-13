from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.constants import UserRole
from apps.core.permissions import IsSchoolAdmin, IsStaffMember, RequiresFeature, TenantActivePermission
from apps.staff.permissions import CanAccessStaffBulkImport, CanManageStaffRecords
from apps.core.import_mixins import BulkImportMixin
from apps.core.views import BaseModelViewSet
from apps.staff.import_handlers import STAFF_IMPORT_SPEC, commit_staff_rows, staff_import_resolver
from apps.tenants.context import TenantContext
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


class StaffViewSet(BulkImportMixin, BaseModelViewSet):
    required_feature_key = "staff_management"
    _STAFF_BULK_IMPORT_ACTIONS = frozenset({
        "import_template", "validate_import", "commit_import",
    })
    queryset = Staff.objects.select_related(
        "department", "user", "user__profile_picture", "supervisor",
    ).prefetch_related(
        "teacher_profile", "teacher_profile__subjects",
    )
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "department", "employment_type", "staff_category", "portal_role"]
    search_fields = [
        "first_name", "last_name", "middle_name", "employee_id",
        "email", "personal_email", "designation", "national_id",
    ]
    import_spec = STAFF_IMPORT_SPEC

    def get_import_row_resolver(self):
        tenant = TenantContext.get_tenant() or self.request.user.tenant
        return staff_import_resolver(tenant)

    def commit_import_rows(self, rows, *, request: Request):
        tenant = TenantContext.get_tenant() or request.user.tenant
        return commit_staff_rows(tenant, rows, actor=request.user)

    def get_permissions(self):
        perms: list = []
        action = getattr(self, "action", None)
        if action in self._STAFF_BULK_IMPORT_ACTIONS:
            perms.extend([CanAccessStaffBulkImport(), TenantActivePermission()])
            return perms
        if action == "destroy":
            perms.extend([IsStaffMember(), TenantActivePermission()])
            perms.append(RequiresFeature("delete_user")())
            return perms
        if action in ("create", "update", "partial_update"):
            perms.extend([CanManageStaffRecords(), TenantActivePermission()])
            perms.append(RequiresFeature(self.required_feature_key)())
            return perms
        perms.extend([IsStaffMember(), TenantActivePermission()])
        if self.required_feature_key:
            perms.append(RequiresFeature(self.required_feature_key)())
        return perms

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
        if staff.has_portal_access and staff.user_id and getattr(staff.user, "must_change_password", False):
            message += " Portal login credentials were emailed to their work address."
        payload = {
            "success": True,
            "message": message,
            "data": output.data,
        }
        temp = getattr(staff, "_onboarding_temp_password", None)
        if temp and staff.user_id and not getattr(staff.user, "must_change_password", False):
            payload["temporary_password"] = temp
        return Response(payload, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = StaffDetailSerializer(instance, context=self.get_serializer_context())
        return Response({"success": True, "data": serializer.data})

    def update(self, request: Request, *args, **kwargs) -> Response:
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        return Response({
            "success": True,
            "message": "Staff profile updated successfully.",
            "data": StaffDetailSerializer(staff, context=self.get_serializer_context()).data,
        })

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

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