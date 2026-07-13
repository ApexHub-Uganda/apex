from __future__ import annotations

from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.academics.mixins import AcademicScopeMixin
from apps.core.import_mixins import BulkImportMixin
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.core.bulk_import import (
    is_supported_import_filename,
    parse_upload,
    unsupported_import_message,
    validate_rows,
)
from apps.students.import_handlers import (
    PARENT_IMPORT_SPEC,
    STUDENT_IMPORT_SPEC,
    StudentImportContext,
    commit_parent_rows,
    commit_student_rows,
    get_student_import_context,
    parent_import_resolver,
    student_import_resolver,
)
from apps.students.profile import count_incomplete_students
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
from apps.academics.class_hub import user_can_enroll_students
from apps.tenants.context import TenantContext


class ParentViewSet(BulkImportMixin, BaseModelViewSet):
    required_feature_key = "parent_management"
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["first_name", "last_name", "email", "phone"]
    import_spec = PARENT_IMPORT_SPEC

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) == "destroy":
            perms.append(RequiresFeature("delete_user")())
            return perms
        if self.required_feature_key:
            perms.append(RequiresFeature(self.required_feature_key)())
        return perms

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


class StudentViewSet(AcademicScopeMixin, BulkImportMixin, BaseModelViewSet):
    required_feature_key = "student_management"
    _ENROLLMENT_FEATURE_ACTIONS = frozenset({
        "create", "validate_import", "commit_import", "import_context", "import_template",
    })
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

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        action = getattr(self, "action", None)
        if action == "destroy":
            perms.append(RequiresFeature("delete_user")())
            return perms
        if action in self._ENROLLMENT_FEATURE_ACTIONS:
            perms.append(RequiresAnyFeature("student_management", "class_teacher_tools")())
        else:
            perms.append(RequiresFeature("student_management")())
        return perms

    def _enrollment_denied_response(
        self,
        request: Request,
        *,
        school_class_id: str | None = None,
    ) -> Response | None:
        class_id = school_class_id or request.data.get("school_class") or request.query_params.get("school_class")
        if user_can_enroll_students(request.user, school_class_id=class_id):
            return None
        return Response(
            {
                "success": False,
                "message": (
                    "You do not have permission to enroll students into this class. "
                    "School administrators and assigned class teachers with student write access may enroll."
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        denied = self._enrollment_denied_response(request)
        if denied is not None:
            return denied
        return super().create(request, *args, **kwargs)

    def _import_context_from_request(self, request: Request) -> StudentImportContext:
        return StudentImportContext(
            school_class_id=request.data.get("school_class") or request.query_params.get("school_class"),
            stream_id=request.data.get("stream") or request.query_params.get("stream"),
        )

    def get_import_row_resolver(self):
        tenant = TenantContext.get_tenant() or self.request.user.tenant
        context = self._import_context_from_request(self.request)
        return student_import_resolver(tenant, context=context, user=self.request.user)

    def commit_import_rows(self, rows, *, request: Request):
        tenant = TenantContext.get_tenant() or request.user.tenant
        return commit_student_rows(tenant, rows, actor=request.user)

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        incomplete_count = count_incomplete_students(queryset)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["meta"] = {
                **(response.data.get("meta") or {}),
                "incomplete_profile_count": incomplete_count,
            }
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "meta": {"incomplete_profile_count": incomplete_count},
        })

    @action(detail=False, methods=["get"], url_path="import-context")
    def import_context(self, request: Request) -> Response:
        return Response({
            "success": True,
            "data": get_student_import_context(request.user),
        })

    @action(
        detail=False,
        methods=["post"],
        url_path="validate-import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def validate_import(self, request: Request) -> Response:
        context = self._import_context_from_request(request)
        denied = self._enrollment_denied_response(
            request,
            school_class_id=context.school_class_id,
        )
        if denied is not None:
            return denied

        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"success": False, "message": "No file uploaded. Attach an Excel or CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_supported_import_filename(upload.name):
            return Response(
                {"success": False, "message": unsupported_import_message()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        spec = self.get_import_spec()
        headers, raw_rows = parse_upload(upload)
        resolver = self.get_import_row_resolver()
        result = validate_rows(spec, headers, raw_rows, row_resolver=resolver)
        context = self._import_context_from_request(request)
        school_class, stream, context_errors = context.validate_access(
            TenantContext.get_tenant() or request.user.tenant,
            request.user,
        )
        if context_errors:
            result["errors"] = list(context_errors) + result["errors"]
            result["error_count"] = len([e for e in result["errors"] if e.get("severity") != "warning"])
            result["can_commit"] = False

        result["import_context"] = {
            "school_class_id": str(school_class.id) if school_class else None,
            "school_class_name": school_class.name if school_class else None,
            "stream_id": str(stream.id) if stream else None,
            "stream_name": stream.name if stream else None,
        }

        return Response({
            "success": True,
            "message": (
                f"Validated {result['total_rows']} rows — "
                f"{result['valid_count']} ready, {result['error_count']} issues."
            ),
            "data": result,
        })

    @action(detail=False, methods=["post"], url_path="commit-import")
    def commit_import(self, request: Request) -> Response:
        context = self._import_context_from_request(request)
        denied = self._enrollment_denied_response(
            request,
            school_class_id=context.school_class_id,
        )
        if denied is not None:
            return denied

        rows = request.data.get("rows")
        if not isinstance(rows, list) or not rows:
            return Response(
                {"success": False, "message": "No validated rows to import."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        context = self._import_context_from_request(request)
        tenant = TenantContext.get_tenant() or request.user.tenant
        _, _, context_errors = context.validate_access(tenant, request.user)
        if context_errors:
            return Response(
                {"success": False, "message": context_errors[0]["message"], "data": {"errors": context_errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        spec = self.get_import_spec()
        resolver = self.get_import_row_resolver()
        revalidated = validate_rows(
            spec,
            list(spec.all_keys),
            [{k: str(v) if v is not None else "" for k, v in row.items() if not k.startswith("_")} for row in rows],
            row_resolver=resolver,
        )

        if not revalidated["can_commit"]:
            return Response(
                {"success": False, "message": "Import blocked — fix validation errors first.", "data": revalidated},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(revalidated["ready"]) != len(rows):
            return Response(
                {"success": False, "message": "Row data changed since validation. Re-validate the file.", "data": revalidated},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outcome = self.commit_import_rows(revalidated["ready"], request=request)
        return Response({
            "success": True,
            "message": outcome.get("message", f"Imported {outcome.get('created', 0)} records."),
            "data": outcome,
        })

    @action(detail=True, methods=["post"])
    def enroll(self, request: Request, pk: str = None) -> Response:
        denied = self._enrollment_denied_response(request)
        if denied is not None:
            return denied

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