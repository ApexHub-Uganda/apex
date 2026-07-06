from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.examinations.models import Exam, Grade, GradingScale, ReportCard
from apps.examinations.reference import (
    _option,
    academic_year_options,
    class_options,
    current_academic_year,
    paper_options,
    subject_options,
    term_options,
)
from apps.examinations.serializers import (
    ExamSerializer,
    GradeSerializer,
    GradingScaleSerializer,
    MarksEntryBulkSerializer,
    ReportCardSerializer,
)
from apps.examinations.services import bulk_upsert_grades
from apps.students.models import Student
from apps.students.serializers import StudentListSerializer


class GradingScaleViewSet(BaseModelViewSet):
    required_feature_key = "grade_calculation"
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]


class ExamViewSet(BaseModelViewSet):
    required_feature_key = "examination_management"
    queryset = Exam.objects.select_related("subject", "paper", "school_class", "term")
    serializer_class = ExamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "term", "subject", "paper", "exam_type"]
    search_fields = ["name"]


class GradeViewSet(BaseModelViewSet):
    required_feature_key = "marks_entry"
    queryset = Grade.objects.select_related(
        "exam", "exam__subject", "exam__paper", "student", "graded_by",
    )
    serializer_class = GradeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["exam", "student", "exam__subject", "exam__school_class", "exam__term", "exam__paper"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]


class ReportCardViewSet(BaseModelViewSet):
    required_feature_key = "report_cards"
    queryset = ReportCard.objects.select_related("student", "term", "school_class")
    serializer_class = ReportCardSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "term", "school_class", "is_published"]


class ExaminationReferenceView(APIView):
    """Subjects, classes, terms, and papers for examination scheduling."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresAnyFeature("examination_management", "marks_entry")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})

        year = current_academic_year(tenant)
        return Response({
            "success": True,
            "data": {
                "subjects": subject_options(tenant),
                "academic_years": academic_year_options(tenant),
                "current_academic_year": str(year.id) if year else None,
                "classes": class_options(tenant),
                "terms": term_options(tenant),
            },
        })


class MarksEntryOptionsView(APIView):
    """Cascading subject → paper → class → term → exam → students."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("marks_entry")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"subjects": []}})

        subject_id = request.query_params.get("subject")
        paper_id = request.query_params.get("paper")
        class_id = request.query_params.get("school_class")
        term_id = request.query_params.get("term")
        exam_id = request.query_params.get("exam")
        academic_year_id = request.query_params.get("academic_year")

        year = current_academic_year(tenant)
        data: dict = {
            "subjects": subject_options(tenant),
            "academic_years": academic_year_options(tenant),
            "current_academic_year": str(year.id) if year else None,
            "papers": [],
            "requires_paper": False,
            "classes": [],
            "terms": [],
            "exams": [],
            "students": [],
            "grades": {},
            "exam_detail": None,
        }

        if not subject_id:
            return Response({"success": True, "data": data})

        papers = paper_options(tenant, subject_id)
        data["papers"] = papers
        data["requires_paper"] = len(papers) > 0

        if not class_id:
            data["classes"] = class_options(
                tenant,
                subject_id=subject_id,
                academic_year_id=academic_year_id or (str(year.id) if year else None),
            )
            return Response({"success": True, "data": data})

        if not term_id:
            data["terms"] = term_options(
                tenant,
                school_class_id=class_id,
                academic_year_id=academic_year_id,
            )
            return Response({"success": True, "data": data})

        exam_qs = Exam.objects.filter(
            tenant=tenant,
            subject_id=subject_id,
            school_class_id=class_id,
            term_id=term_id,
        ).select_related("subject", "paper", "school_class", "term")

        if paper_id:
            exam_qs = exam_qs.filter(paper_id=paper_id)
        else:
            exam_qs = exam_qs.filter(paper__isnull=True)

        exams = exam_qs.order_by("-exam_date")
        data["exams"] = [
            _option(
                e.id,
                f"{e.name} — {e.exam_date} ({e.get_exam_type_display()})",
                max_score=str(e.max_score),
                paper_code=e.paper.code if e.paper_id else "",
            )
            for e in exams
        ]

        if not exam_id:
            return Response({"success": True, "data": data})

        try:
            exam = exams.get(pk=exam_id)
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Exam not found for the selected filters."},
                status=status.HTTP_404_NOT_FOUND,
            )

        students = Student.objects.filter(
            tenant=tenant,
            school_class_id=exam.school_class_id,
            status="active",
        ).order_by("last_name", "first_name")

        grades = Grade.objects.filter(tenant=tenant, exam=exam).select_related("student")
        grade_map = {
            str(g.student_id): {
                "id": str(g.id),
                "score": str(g.score),
                "grade": g.grade,
                "remarks": g.remarks,
            }
            for g in grades
        }

        data["exam_detail"] = ExamSerializer(exam).data
        data["students"] = StudentListSerializer(students, many=True, context={"request": request}).data
        data["grades"] = grade_map
        return Response({"success": True, "data": data})


class MarksEntryBulkView(APIView):
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
            exam = Exam.objects.select_related("subject", "school_class").get(pk=exam_id, tenant=tenant)
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Exam not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = bulk_upsert_grades(tenant=tenant, exam=exam, entries=entries, user=request.user)
        message = f"Saved {result['saved']} mark(s)."
        if result["errors"]:
            message += f" {len(result['errors'])} row(s) had errors."

        return Response({
            "success": not result["errors"],
            "message": message,
            "data": result,
        })