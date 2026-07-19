from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.mixins import AcademicScopeMixin, ExaminationSessionSingletonMixin
from apps.academics.scoping import filter_queryset_for_user, user_can_access_exam, user_can_write_exam_marks, user_has_unrestricted_marks_access
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.examinations.models import Exam, ExaminationSession, Grade, GradingScale, GradingScheme, ReportCard
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
    ExamWorkflowActionSerializer,
    ExaminationSessionSerializer,
    GradeSerializer,
    GradeCalculationApplySerializer,
    GradingScaleSerializer,
    GradingSchemeSerializer,
    GradingSchemeSyncSerializer,
    MarksEntryBulkSerializer,
    ReportCardSerializer,
)
from apps.examinations.grading import GradingSchemeError, apply_grading_scheme, sync_scheme_bands
from apps.examinations.marks_scoping import (
    marks_class_options,
    marks_scope_meta,
    marks_subject_options,
    marks_term_options,
)
from apps.examinations.services import bulk_upsert_grades
from apps.examinations.constants import MARKS_STATUS_SUBMITTED
from apps.examinations.workflow import (
    MarksWorkflowError,
    approve_exam_marks,
    archive_exam,
    bulk_workflow_action,
    lock_exam_marks,
    publish_exam,
    reopen_exam_marks,
    submit_exam_marks,
    user_can_reopen_marks,
)
from apps.students.models import Student
from apps.students.serializers import StudentListSerializer


class GradingScaleViewSet(BaseModelViewSet):
    required_feature_key = "grade_calculation"
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]


class GradingSchemeViewSet(BaseModelViewSet):
    """Named grading schemes with score bands — managed under Academics → Grading."""

    queryset = GradingScheme.objects.prefetch_related("bands")
    serializer_class = GradingSchemeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "description"]
    filterset_fields = ["is_default"]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve"):
            perms.append(RequiresAnyFeature("grading", "grade_calculation")())
        else:
            perms.append(RequiresFeature("grading")())
        return perms

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="sync")
    def sync_scheme(self, request):
        payload = GradingSchemeSyncSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = request.user.tenant
        data = payload.validated_data
        scheme_id = request.data.get("id")

        if scheme_id:
            scheme = GradingScheme.objects.filter(pk=scheme_id, tenant=tenant, is_deleted=False).first()
            if scheme is None:
                return Response(
                    {"success": False, "message": "Grading scheme not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            scheme.name = data["name"]
            scheme.description = data.get("description", "")
            scheme.is_default = data.get("is_default", False)
            scheme.updated_by = request.user
            scheme.save(update_fields=["name", "description", "is_default", "updated_by", "updated_at"])
        else:
            if GradingScheme.objects.filter(tenant=tenant, name=data["name"], is_deleted=False).exists():
                return Response(
                    {"success": False, "message": "A grading scheme with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            scheme = GradingScheme.objects.create(
                tenant=tenant,
                name=data["name"],
                description=data.get("description", ""),
                is_default=data.get("is_default", False),
                created_by=request.user,
                updated_by=request.user,
            )

        if data.get("is_default"):
            GradingScheme.objects.filter(tenant=tenant, is_deleted=False).exclude(pk=scheme.pk).update(is_default=False)

        try:
            sync_scheme_bands(
                tenant=tenant,
                scheme=scheme,
                bands=data["bands"],
                user=request.user,
            )
        except GradingSchemeError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scheme.refresh_from_db()
        return Response({
            "success": True,
            "message": "Grading scheme saved.",
            "data": GradingSchemeSerializer(scheme).data,
        }, status=status.HTTP_200_OK)


class ExaminationSessionViewSet(ExaminationSessionSingletonMixin, AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "examination_sessions"
    queryset = ExaminationSession.objects.select_related("academic_year", "term")
    serializer_class = ExaminationSessionSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year", "term", "status"]
    search_fields = ["name"]


class ExamViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "examination_management"
    queryset = Exam.objects.select_related(
        "subject", "paper", "school_class", "term", "examination_session",
    )
    serializer_class = ExamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = [
        "school_class", "term", "subject", "paper", "exam_type",
        "lifecycle_status", "marks_status", "examination_session",
    ]
    search_fields = ["name"]

    _WORKFLOW_FEATURES = {
        "publish": "assessment_management",
        "archive": "assessment_management",
        "submit_marks": "marks_entry",
        "approve_marks": "marks_approval",
        "lock_marks": "marks_approval",
        "reopen_marks": "marks_approval",
    }

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        feature_key = self._WORKFLOW_FEATURES.get(
            getattr(self, "action", None),
            self.required_feature_key,
        )
        if feature_key:
            perms.append(RequiresFeature(feature_key)())
        return perms

    def _workflow_response(self, exam: Exam, *, message: str) -> Response:
        return Response({
            "success": True,
            "message": message,
            "data": ExamSerializer(exam).data,
        })

    def _handle_workflow_error(self, exc: MarksWorkflowError) -> Response:
        return Response(
            {"success": False, "message": exc.message, "code": exc.code},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        exam = self.get_object()
        if not user_can_access_exam(request.user, exam):
            return Response(
                {"success": False, "message": "You do not have access to this exam."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            publish_exam(exam=exam, user=request.user)
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Assessment published.")

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        exam = self.get_object()
        try:
            archive_exam(exam=exam, user=request.user)
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Assessment archived.")

    @action(detail=True, methods=["post"], url_path="submit-marks")
    def submit_marks(self, request, pk=None):
        exam = self.get_object()
        if not user_can_access_exam(request.user, exam):
            return Response(
                {"success": False, "message": "You do not have access to this exam."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            submit_exam_marks(exam=exam, user=request.user)
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Marks submitted for approval.")

    @action(detail=True, methods=["post"], url_path="approve-marks")
    def approve_marks(self, request, pk=None):
        exam = self.get_object()
        try:
            approve_exam_marks(exam=exam, user=request.user)
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Marks approved.")

    @action(detail=True, methods=["post"], url_path="lock-marks")
    def lock_marks(self, request, pk=None):
        exam = self.get_object()
        try:
            lock_exam_marks(exam=exam, user=request.user)
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Marks locked.")

    @action(detail=True, methods=["post"], url_path="reopen-marks")
    def reopen_marks(self, request, pk=None):
        if not user_can_reopen_marks(request.user):
            return Response(
                {"success": False, "message": "Only the Director of Studies can reopen finalized marks.", "code": "forbidden_reopen"},
                status=status.HTTP_403_FORBIDDEN,
            )
        exam = self.get_object()
        payload = ExamWorkflowActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            reopen_exam_marks(
                exam=exam,
                user=request.user,
                reason=payload.validated_data.get("reason", ""),
            )
        except MarksWorkflowError as exc:
            return self._handle_workflow_error(exc)
        exam.refresh_from_db()
        return self._workflow_response(exam, message="Marks reopened for editing.")


class GradeViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "marks_entry"
    queryset = Grade.objects.select_related(
        "exam", "exam__subject", "exam__paper", "student", "graded_by",
    )
    serializer_class = GradeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["exam", "student", "exam__subject", "exam__school_class", "exam__term", "exam__paper"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]


class ReportCardViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "report_cards"
    queryset = ReportCard.objects.select_related("student", "term", "school_class")
    serializer_class = ReportCardSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "term", "school_class", "is_published"]


class MarksApprovalQueueView(APIView):
    """List exams awaiting marks approval (scoped to role)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("marks_approval")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"results": [], "count": 0}})

        qs = filter_queryset_for_user(
            Exam.objects.filter(
                tenant=tenant,
                marks_status=MARKS_STATUS_SUBMITTED,
                is_deleted=False,
            ).select_related("subject", "school_class", "term", "marks_submitted_by"),
            request.user,
        )
        results = [
            {
                **ExamSerializer(e).data,
                "grade_count": e.grades.filter(is_deleted=False).count(),
            }
            for e in qs.order_by("-marks_submitted_at")[:100]
        ]
        return Response({
            "success": True,
            "data": {"results": results, "count": qs.count()},
        })


class WorkflowBulkActionView(APIView):
    """Bulk approve, lock, publish, or archive exams."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresAnyFeature("marks_approval", "assessment_management")())
        return perms

    def post(self, request):
        from apps.tenants.role_permissions import user_can_access_feature
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = (request.data.get("action") or "").strip().lower()
        exam_ids = request.data.get("exam_ids") or []
        action_features = {
            "approve": ("marks_approval", True),
            "lock": ("marks_approval", True),
            "publish": ("assessment_management", True),
            "archive": ("assessment_management", True),
        }
        if action not in action_features:
            return Response(
                {"success": False, "message": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not exam_ids:
            return Response(
                {"success": False, "message": "Select at least one exam."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feat_key, needs_write = action_features[action]
        if not user_can_access_feature(tenant, request.user, feat_key, require_write=needs_write):
            return Response(
                {"success": False, "message": f"You do not have permission for {action}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = filter_queryset_for_user(
            Exam.objects.filter(tenant=tenant, id__in=exam_ids, is_deleted=False),
            request.user,
        )
        if qs.count() != len(set(str(i) for i in exam_ids)):
            return Response(
                {"success": False, "message": "One or more exams are not accessible."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = bulk_workflow_action(exams=list(qs), user=request.user, action=action)
        except MarksWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = f"Processed {len(result['processed'])} exam(s)."
        if result["errors"]:
            message += f" {len(result['errors'])} failed."

        return Response({
            "success": not result["errors"],
            "message": message,
            "data": result,
        })


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
        user = request.user
        return Response({
            "success": True,
            "data": {
                "subjects": subject_options(tenant, user=user),
                "academic_years": academic_year_options(tenant),
                "current_academic_year": str(year.id) if year else None,
                "classes": class_options(tenant, user=user),
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

        user = request.user
        year = current_academic_year(tenant)
        scope_meta = marks_scope_meta(tenant, user)
        if not user_has_unrestricted_marks_access(user) and term_id and scope_meta.get("current_term_id"):
            if str(term_id) != scope_meta["current_term_id"]:
                return Response(
                    {"success": False, "message": "You may only work with marks for the current academic term."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        data: dict = {
            "scope_meta": scope_meta,
            "subjects": marks_subject_options(tenant, user),
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
            data["classes"] = marks_class_options(
                tenant,
                subject_id=subject_id,
                academic_year_id=academic_year_id or (str(year.id) if year else None),
                user=user,
            )
            return Response({"success": True, "data": data})

        if not term_id:
            data["terms"] = marks_term_options(
                tenant,
                school_class_id=class_id,
                academic_year_id=academic_year_id,
                user=user,
            )
            return Response({"success": True, "data": data})

        exam_qs = filter_queryset_for_user(
            Exam.objects.filter(
                tenant=tenant,
                subject_id=subject_id,
                school_class_id=class_id,
                term_id=term_id,
            ).select_related("subject", "paper", "school_class", "term"),
            user,
        )

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

        if not user_can_write_exam_marks(user, exam):
            return Response(
                {"success": False, "message": "You may only enter marks for your assigned classes and subjects in the current term."},
                status=status.HTTP_403_FORBIDDEN,
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

        exam_id = request.data.get("exam")
        if exam_id:
            try:
                exam = Exam.objects.select_related("subject", "school_class").get(pk=exam_id, tenant=tenant)
            except Exam.DoesNotExist:
                exam = None
            else:
                if not user_can_write_exam_marks(request.user, exam):
                    return Response(
                        {"success": False, "message": "You may only enter marks for your assigned classes and subjects in the current term."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        payload = MarksEntryBulkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        exam_id = payload.validated_data["exam"]
        entries = payload.validated_data["entries"]

        try:
            exam = Exam.objects.select_related("subject", "school_class", "term").get(pk=exam_id, tenant=tenant)
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Exam not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_can_write_exam_marks(request.user, exam):
            return Response(
                {"success": False, "message": "You may only enter marks for your assigned classes and subjects in the current term."},
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


class GradeCalculationOptionsView(APIView):
    """Cascading options for grade calculation — schemes plus subject/class/exam filters."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("grade_calculation")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"schemes": [], "subjects": []}})

        subject_id = request.query_params.get("subject")
        paper_id = request.query_params.get("paper")
        class_id = request.query_params.get("school_class")
        term_id = request.query_params.get("term")
        exam_id = request.query_params.get("exam")
        scheme_id = request.query_params.get("scheme")
        academic_year_id = request.query_params.get("academic_year")

        user = request.user
        year = current_academic_year(tenant)
        scope_meta = marks_scope_meta(tenant, user)
        if not user_has_unrestricted_marks_access(user) and term_id and scope_meta.get("current_term_id"):
            if str(term_id) != scope_meta["current_term_id"]:
                return Response(
                    {"success": False, "message": "You may only calculate grades for the current academic term."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        schemes = GradingScheme.objects.filter(tenant=tenant, is_deleted=False).prefetch_related("bands").order_by("name")
        data: dict = {
            "scope_meta": scope_meta,
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
            "subjects": marks_subject_options(tenant, user),
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
            "selected_scheme": None,
        }

        if scheme_id:
            scheme = schemes.filter(pk=scheme_id).first()
            if scheme is not None:
                data["selected_scheme"] = GradingSchemeSerializer(scheme).data

        if not subject_id:
            return Response({"success": True, "data": data})

        papers = paper_options(tenant, subject_id)
        data["papers"] = papers
        data["requires_paper"] = len(papers) > 0

        if not class_id:
            data["classes"] = marks_class_options(
                tenant,
                subject_id=subject_id,
                academic_year_id=academic_year_id or (str(year.id) if year else None),
                user=user,
            )
            return Response({"success": True, "data": data})

        if not term_id:
            data["terms"] = marks_term_options(
                tenant,
                school_class_id=class_id,
                academic_year_id=academic_year_id,
                user=user,
            )
            return Response({"success": True, "data": data})

        exam_qs = filter_queryset_for_user(
            Exam.objects.filter(
                tenant=tenant,
                subject_id=subject_id,
                school_class_id=class_id,
                term_id=term_id,
            ).select_related("subject", "paper", "school_class", "term"),
            user,
        )
        if paper_id:
            exam_qs = exam_qs.filter(paper_id=paper_id)
        else:
            exam_qs = exam_qs.filter(paper__isnull=True)

        data["exams"] = [
            _option(
                e.id,
                f"{e.name} — {e.exam_date} ({e.get_exam_type_display()})",
                max_score=str(e.max_score),
                marks_status=e.marks_status,
                has_marks=e.grades.filter(is_deleted=False).exists(),
            )
            for e in exam_qs.order_by("-exam_date")
        ]

        if not exam_id:
            return Response({"success": True, "data": data})

        try:
            exam = exam_qs.get(pk=exam_id)
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Exam not found for the selected filters."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_can_write_exam_marks(user, exam):
            return Response(
                {"success": False, "message": "You may only calculate grades for your assigned classes and subjects in the current term."},
                status=status.HTTP_403_FORBIDDEN,
            )

        students = Student.objects.filter(
            tenant=tenant,
            school_class_id=exam.school_class_id,
            status="active",
        ).order_by("last_name", "first_name")

        grade_rows = Grade.objects.filter(tenant=tenant, exam=exam, is_deleted=False).select_related("student")
        grade_map = {
            str(g.student_id): {
                "id": str(g.id),
                "score": str(g.score),
                "grade": g.grade,
                "remarks": g.remarks,
            }
            for g in grade_rows
        }

        data["exam_detail"] = ExamSerializer(exam).data
        data["students"] = StudentListSerializer(students, many=True, context={"request": request}).data
        data["grades"] = grade_map
        data["marks_count"] = grade_rows.count()
        return Response({"success": True, "data": data})


class GradeCalculationApplyView(APIView):
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
            exam = Exam.objects.select_related("subject", "school_class", "term").get(
                pk=payload.validated_data["exam"],
                tenant=tenant,
            )
        except Exam.DoesNotExist:
            return Response(
                {"success": False, "message": "Exam not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_can_write_exam_marks(request.user, exam):
            return Response(
                {"success": False, "message": "You may only calculate grades for your assigned classes and subjects in the current term."},
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