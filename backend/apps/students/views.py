from __future__ import annotations

from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.import_mixins import BulkImportMixin
from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.students.import_handlers import (
    PARENT_IMPORT_SPEC,
    STUDENT_IMPORT_SPEC,
    commit_parent_rows,
    commit_student_rows,
    parent_import_resolver,
    student_import_resolver,
)
from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student
from apps.students.serializers import (
    AdmissionSerializer,
    GuardianSerializer,
    MedicalRecordSerializer,
    ParentDetailSerializer,
    ParentListSerializer,
    ParentSerializer,
    StudentDetailSerializer,
    StudentListSerializer,
    StudentSerializer,
)
from apps.tenants.context import TenantContext


class ParentViewSet(BulkImportMixin, BaseModelViewSet):
    required_feature_key = "parent_management"
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["first_name", "last_name", "email", "phone"]
    import_spec = PARENT_IMPORT_SPEC

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs.select_related("user__profile_picture").prefetch_related("children").annotate(
                _children_count=models.Count("children", distinct=True),
            )
        if self.action in ("retrieve", "link_student", "unlink_student", "set_children"):
            return qs.prefetch_related(
                "children__school_class",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ParentListSerializer
        if self.action in ("retrieve", "link_student", "unlink_student", "set_children", "partial_update", "update"):
            return ParentDetailSerializer
        return ParentSerializer

    def get_import_row_resolver(self):
        tenant = TenantContext.get_tenant() or self.request.user.tenant
        return parent_import_resolver(tenant)

    def commit_import_rows(self, rows, *, request: Request):
        tenant = TenantContext.get_tenant() or request.user.tenant
        return commit_parent_rows(tenant, rows, actor=request.user)

    @action(detail=True, methods=["post"], url_path="link-student")
    def link_student(self, request: Request, pk: str = None) -> Response:
        parent = self.get_object()
        student_id = request.data.get("student_id")
        if not student_id:
            return Response({"detail": "student_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        student = Student.objects.filter(pk=student_id).first()
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        student.parents.add(parent)
        parent = self.get_queryset().get(pk=parent.pk)
        return Response(ParentDetailSerializer(parent, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="unlink-student")
    def unlink_student(self, request: Request, pk: str = None) -> Response:
        parent = self.get_object()
        student_id = request.data.get("student_id")
        if not student_id:
            return Response({"detail": "student_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        student = Student.objects.filter(pk=student_id).first()
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        student.parents.remove(parent)
        parent = self.get_queryset().get(pk=parent.pk)
        return Response(ParentDetailSerializer(parent, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="set-children")
    def set_children(self, request: Request, pk: str = None) -> Response:
        parent = self.get_object()
        child_ids = request.data.get("child_ids")
        if not isinstance(child_ids, list):
            return Response({"detail": "child_ids must be a list of student IDs."}, status=status.HTTP_400_BAD_REQUEST)
        students = Student.objects.filter(pk__in=child_ids)
        parent.children.set(students)
        return Response(ParentDetailSerializer(parent, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="matching-summary")
    def matching_summary(self, request: Request) -> Response:
        tenant = TenantContext.get_tenant() or request.user.tenant
        parents = Parent.objects.filter(tenant=tenant).prefetch_related("children")
        students = Student.objects.filter(tenant=tenant).prefetch_related("parents")
        linked_student_ids = set()
        for parent in parents:
            for child in parent.children.all():
                linked_student_ids.add(child.id)
        unmatched = [
            {
                "id": s.id,
                "full_name": s.full_name,
                "admission_number": s.admission_number,
                "class_name": s.school_class.name if s.school_class else None,
                "status": s.status,
            }
            for s in students
            if s.id not in linked_student_ids
        ]
        unlinked_parents = [
            {
                "id": p.id,
                "full_name": p.full_name,
                "phone": p.phone,
                "email": p.email,
            }
            for p in parents
            if p.children.count() == 0
        ]
        return Response({
            "parent_count": parents.count(),
            "student_count": students.count(),
            "linked_pairs": sum(p.children.count() for p in parents),
            "unmatched_students": unmatched,
            "unlinked_parents": unlinked_parents,
        })


class StudentViewSet(BulkImportMixin, BaseModelViewSet):
    required_feature_key = "student_management"
    queryset = Student.objects.select_related(
        "school_class", "stream", "user__profile_picture",
    ).prefetch_related("parents")
    serializer_class = StudentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "school_class", "stream", "gender", "boarding_status"]
    search_fields = ["first_name", "last_name", "admission_number", "email", "upi_number"]
    import_spec = STUDENT_IMPORT_SPEC

    def get_serializer_class(self):
        if self.action == "list":
            return StudentListSerializer
        if self.action == "retrieve":
            return StudentDetailSerializer
        return StudentSerializer

    def get_import_row_resolver(self):
        tenant = TenantContext.get_tenant() or self.request.user.tenant
        return student_import_resolver(tenant)

    def commit_import_rows(self, rows, *, request: Request):
        tenant = TenantContext.get_tenant() or request.user.tenant
        return commit_student_rows(tenant, rows, actor=request.user)

    @action(detail=True, methods=["post"])
    def enroll(self, request: Request, pk: str = None) -> Response:
        student = self.get_object()
        class_id = request.data.get("school_class")
        stream_id = request.data.get("stream")
        if class_id:
            student.school_class_id = class_id
        if stream_id:
            student.stream_id = stream_id
        student.status = "active"
        student.save()
        return Response(StudentDetailSerializer(student).data)


class GuardianViewSet(BaseModelViewSet):
    required_feature_key = "parent_management"
    queryset = Guardian.objects.select_related("student")
    serializer_class = GuardianSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "is_primary"]


class AdmissionViewSet(BaseModelViewSet):
    required_feature_key = "admissions"
    queryset = Admission.objects.select_related("student")
    serializer_class = AdmissionSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]


class MedicalRecordViewSet(BaseModelViewSet):
    required_feature_key = "medical_records"
    queryset = MedicalRecord.objects.select_related("student")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "is_chronic"]