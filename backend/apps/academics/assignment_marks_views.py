"""API views for Academics → Assignments marks entry and grade calculation."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.scoping import user_can_write_assignment_marks
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.examinations.assignment_marks import (
    AssignmentMarksError,
    assignment_options_payload,
    get_or_create_assignment_assessment,
)
from apps.examinations.grading import GradingSchemeError, apply_grading_scheme
from apps.examinations.models import Exam, GradingScheme
from apps.examinations.serializers import GradeCalculationApplySerializer, MarksEntryBulkSerializer
from apps.examinations.services import bulk_upsert_grades
from apps.examinations.workflow import MarksWorkflowError


class AssignmentMarksOptionsView(APIView):
    """Cascading subject → paper → class → assessment → students (no term)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("marks_entry")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"subjects": []}})

        try:
            data = assignment_options_payload(
                tenant,
                request.user,
                subject_id=request.query_params.get("subject"),
                paper_id=request.query_params.get("paper"),
                school_class_id=request.query_params.get("school_class"),
                assessment_id=request.query_params.get("assessment"),
            )
        except AssignmentMarksError as exc:
            status_code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=status_code)

        return Response({"success": True, "data": data})


class AssignmentMarksCreateView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("marks_entry")())
        return perms

    def post(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = request.data.get("name", "")
        subject_id = request.data.get("subject")
        school_class_id = request.data.get("school_class")
        paper_id = request.data.get("paper")
        max_score = request.data.get("max_score", 100)

        if not subject_id or not school_class_id:
            return Response(
                {"success": False, "message": "Subject and class are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            exam = get_or_create_assignment_assessment(
                tenant=tenant,
                user=request.user,
                name=name,
                subject_id=subject_id,
                school_class_id=school_class_id,
                paper_id=paper_id,
                max_score=max_score,
            )
        except AssignmentMarksError as exc:
            status_code = status.HTTP_400_BAD_REQUEST
            if exc.code == "forbidden":
                status_code = status.HTTP_403_FORBIDDEN
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=status_code)

        from apps.examinations.serializers import ExamSerializer

        return Response({
            "success": True,
            "message": f"“{exam.name}” is ready for marks entry.",
            "data": ExamSerializer(exam).data,
        })


class AssignmentMarksBulkView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("marks_entry")())
        return perms

    def post(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = MarksEntryBulkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        exam_id = payload.validated_data["exam"]
        entries = payload.validated_data["entries"]

        try:
            exam = Exam.objects.select_related("subject", "school_class").get(
                pk=exam_id,
                tenant=tenant,
                exam_type="assignment",
            )
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_can_write_assignment_marks(request.user, exam):
            return Response(
                {"success": False, "message": "You may only enter marks for your assigned subjects and classes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = bulk_upsert_grades(tenant=tenant, exam=exam, entries=entries, user=request.user)
        except MarksWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = f"Saved {result['saved']} mark(s)."
        if result["errors"]:
            message += f" {len(result['errors'])} row(s) had errors."

        return Response({
            "success": not result["errors"],
            "message": message,
            "data": result,
        })


class AssignmentGradeCalculationOptionsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("grade_calculation")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"schemes": [], "subjects": []}})

        scheme_id = request.query_params.get("scheme")
        subject_id = request.query_params.get("subject")
        paper_id = request.query_params.get("paper")
        school_class_id = request.query_params.get("school_class")
        assessment_id = request.query_params.get("assessment")

        schemes = GradingScheme.objects.filter(tenant=tenant, is_deleted=False).prefetch_related("bands").order_by("name")
        data: dict = {
            "scope_meta": assignment_options_payload(tenant, request.user)["scope_meta"],
            "schemes": [
                {
                    "value": str(s.id),
                    "label": s.name,
                    "is_default": s.is_default,
                    "band_count": s.bands.filter(is_deleted=False).count(),
                    "bands": [
                        {
                            "grade": b.grade,
                            "min_score": str(b.min_score),
                            "max_score": str(b.max_score),
                            "remarks": b.remarks,
                        }
                        for b in s.bands.filter(is_deleted=False).order_by("-min_score")
                    ],
                }
                for s in schemes
            ],
            "subjects": [],
            "papers": [],
            "requires_paper": False,
            "classes": [],
            "assessments": [],
            "students": [],
            "grades": {},
            "exam_detail": None,
            "selected_scheme": None,
            "marks_count": 0,
        }

        if scheme_id:
            from apps.examinations.serializers import GradingSchemeSerializer

            scheme = schemes.filter(pk=scheme_id).first()
            if scheme is not None:
                data["selected_scheme"] = GradingSchemeSerializer(scheme).data

        try:
            marks_data = assignment_options_payload(
                tenant,
                request.user,
                subject_id=subject_id,
                paper_id=paper_id,
                school_class_id=school_class_id,
                assessment_id=assessment_id,
            )
        except AssignmentMarksError as exc:
            status_code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=status_code)

        data.update({
            "subjects": marks_data["subjects"],
            "papers": marks_data["papers"],
            "requires_paper": marks_data["requires_paper"],
            "classes": marks_data["classes"],
            "assessments": [
                {
                    **row,
                    "has_marks": (row.get("marks_count") or 0) > 0,
                }
                for row in marks_data["assessments"]
            ],
            "students": marks_data["students"],
            "grades": marks_data["grades"],
            "exam_detail": marks_data["exam_detail"],
            "marks_count": marks_data.get("marks_count", 0),
        })

        if assessment_id and data["assessments"]:
            data["assessments"] = [
                row for row in data["assessments"]
                if row.get("has_marks", False) or str(row.get("value")) == str(assessment_id)
            ]

        if school_class_id and not assessment_id:
            data["assessments"] = [row for row in data["assessments"] if row.get("has_marks", False)]

        return Response({"success": True, "data": data})


class AssignmentGradeCalculationApplyView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("grade_calculation")())
        return perms

    def post(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = GradeCalculationApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        scheme = GradingScheme.objects.filter(
            pk=payload.validated_data["scheme"],
            tenant=tenant,
            is_deleted=False,
        ).prefetch_related("bands").first()
        if scheme is None:
            return Response(
                {"success": False, "message": "Grading scheme not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            exam = Exam.objects.select_related("subject", "school_class").get(
                pk=payload.validated_data["exam"],
                tenant=tenant,
                exam_type="assignment",
            )
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_can_write_assignment_marks(request.user, exam):
            return Response(
                {"success": False, "message": "You may only calculate grades for your assigned subjects and classes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = apply_grading_scheme(tenant=tenant, exam=exam, scheme=scheme, user=request.user)
        except GradingSchemeError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = (
            f"Applied “{scheme.name}” to {result['updated_count']} of {result['total_count']} mark(s)."
        )
        if result["unmapped_count"]:
            message += f" {result['unmapped_count']} score(s) did not match any band."

        return Response({
            "success": True,
            "message": message,
            "data": result,
        })