"""DoS operational endpoints + certificates + Uganda seed + assessment schemes."""
from __future__ import annotations

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import AssessmentScheme, StudentSubjectRegistration, SubjectCombination
from apps.academics.services.certificates import (
    build_academic_transcript_pdf,
    build_completion_certificate_pdf,
    build_leaving_certificate_pdf,
)
from apps.academics.services.dos_ops import (
    class_performance_analysis,
    marks_completeness_dashboard,
    report_generation_status,
    teacher_load_report,
    uneb_candidate_export,
)
from apps.academics.services.uganda_seed import seed_uganda_presets, uganda_term_templates
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.students.models import Student
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin


def _can_dos(user) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = user.tenant
    if tenant is None:
        return False
    return (
        user_can_access_feature(tenant, user, "dos_workspace", require_write=False)
        or user_can_access_feature(tenant, user, "result_processing", require_write=False)
    )


class DosPerformanceView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def get(self, request: Request) -> Response:
        if not _can_dos(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = class_performance_analysis(
            tenant=request.user.tenant,
            term_id=request.query_params.get("term"),
            school_class_id=request.query_params.get("school_class"),
            stream_id=request.query_params.get("stream"),
        )
        return Response({"success": True, "data": data})


class DosMarksCompletenessView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def get(self, request: Request) -> Response:
        if not _can_dos(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = marks_completeness_dashboard(
            tenant=request.user.tenant,
            term_id=request.query_params.get("term"),
        )
        return Response({"success": True, "data": data})


class DosTeacherLoadView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def get(self, request: Request) -> Response:
        if not _can_dos(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = teacher_load_report(tenant=request.user.tenant)
        return Response({"success": True, "data": data})


class DosReportStatusView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def get(self, request: Request) -> Response:
        if not _can_dos(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = report_generation_status(
            tenant=request.user.tenant,
            term_id=request.query_params.get("term"),
        )
        return Response({"success": True, "data": data})


class UnebCandidateExportView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def get(self, request: Request):
        if not _can_dos(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        fname, csv_text = uneb_candidate_export(
            tenant=request.user.tenant,
            school_class_id=request.query_params.get("school_class"),
            level_hint=request.query_params.get("level") or "",
            exam_year=request.query_params.get("exam_year") or "",
        )
        resp = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp


class LeavingCertificatePdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_management")(),
        ]

    def get(self, request: Request, student_id=None):
        student = Student.objects.filter(
            tenant=request.user.tenant, pk=student_id, is_deleted=False,
        ).first()
        if not student:
            return Response({"success": False, "message": "Student not found."}, status=404)
        pdf = build_leaving_certificate_pdf(
            tenant=request.user.tenant,
            student=student,
            reason=request.query_params.get("reason") or "",
            request=request,
        )
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"leaving-cert-{student.admission_number}.pdf".replace(" ", "-"),
        )


class AcademicTranscriptPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def get(self, request: Request, student_id=None):
        student = Student.objects.filter(
            tenant=request.user.tenant, pk=student_id, is_deleted=False,
        ).first()
        if not student:
            return Response({"success": False, "message": "Student not found."}, status=404)
        pdf = build_academic_transcript_pdf(
            tenant=request.user.tenant, student=student, request=request,
        )
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"transcript-{student.admission_number}.pdf".replace(" ", "-"),
        )


class CompletionCertificatePdfView(APIView):
    """Certificate of Completion for learners who finished the top/final class."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_promotion")(),
        ]

    def get(self, request: Request, student_id=None):
        student = (
            Student.objects.filter(tenant=request.user.tenant, pk=student_id, is_deleted=False)
            .select_related("school_class", "school_class__academic_year")
            .first()
        )
        if not student:
            return Response({"success": False, "message": "Student not found."}, status=404)
        pdf = build_completion_certificate_pdf(
            tenant=request.user.tenant,
            student=student,
            final_class_name=request.query_params.get("class_name") or "",
            academic_year_name=request.query_params.get("year_name") or "",
            request=request,
        )
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"completion-cert-{student.admission_number}.pdf".replace(" ", "-"),
        )


class UgandaSeedView(APIView):
    """Apply Uganda presets (assessment schemes, combinations, UNEB grading)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("dos_workspace")(),
        ]

    def post(self, request: Request) -> Response:
        if not user_is_school_admin(request.user) and not user_can_access_feature(
            request.user.tenant, request.user, "dos_workspace", require_write=True,
        ):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        result = seed_uganda_presets(tenant=request.user.tenant, user=request.user)
        return Response({
            "success": True,
            "data": result,
            "term_templates": [
                {**t, "start_date": str(t["start_date"]), "end_date": str(t["end_date"]),
                 "mid_term_break_start": str(t["mid_term_break_start"]),
                 "mid_term_break_end": str(t["mid_term_break_end"]),
                 "reporting_date": str(t["reporting_date"]),
                 "closing_date": str(t["closing_date"])}
                for t in uganda_term_templates()
            ],
            "message": "Uganda academic presets applied.",
        })


class AssessmentSchemeViewSet(BaseModelViewSet):
    required_feature_key = "grading"
    queryset = AssessmentScheme.objects.all()
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name"]
    filterset_fields = ["is_default"]

    def get_serializer_class(self):
        from apps.academics.serializers import AssessmentSchemeSerializer
        return AssessmentSchemeSerializer


class SubjectCombinationViewSet(BaseModelViewSet):
    required_feature_key = "subjects"
    queryset = SubjectCombination.objects.all()
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["code", "name"]
    filterset_fields = ["level", "is_active"]

    def get_serializer_class(self):
        from apps.academics.serializers import SubjectCombinationSerializer
        return SubjectCombinationSerializer


class StudentSubjectRegistrationViewSet(BaseModelViewSet):
    required_feature_key = "subjects"
    queryset = StudentSubjectRegistration.objects.select_related(
        "student", "subject", "academic_year", "term",
    )
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "academic_year", "term", "subject", "is_active", "combination_code"]
    search_fields = ["student__admission_number", "student__first_name", "student__last_name", "subject__name"]

    def get_serializer_class(self):
        from apps.academics.serializers import StudentSubjectRegistrationSerializer
        return StudentSubjectRegistrationSerializer
