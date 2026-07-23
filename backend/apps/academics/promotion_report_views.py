"""Promotion & report-card API endpoints."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Class, PromotionBatch, Stream, Term
from apps.academics.services.promotion import (
    PromotionError,
    commit_promotion,
    preview_promotion,
    undo_promotion,
)
from apps.academics.services.report_cards import (
    ReportCardError,
    generate_class_report_cards,
    publish_report_cards,
)
from apps.academics.services.report_pdf import build_class_broadsheet_pdf, build_report_card_pdf
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.examinations.models import ReportCard
from apps.examinations.serializers import ReportCardSerializer
from apps.students.models import Student
from apps.academics.scoping import (
    results_role_capabilities,
    user_can_edit_class_teacher_remarks,
    user_can_print_report_cards,
    user_can_read_class_results,
)
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin


def _can_promote(user) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = user.tenant
    if tenant is None:
        return False
    return user_can_access_feature(tenant, user, "student_promotion", require_write=True) or user_can_access_feature(
        tenant, user, "dos_workspace", require_write=True,
    )


def _can_print_or_generate_reports(user, school_class_id=None) -> bool:
    """Class teachers (headed classes) and DoS/leadership may generate/print."""
    return user_can_print_report_cards(user, school_class_id)


def _can_view_reports(user, school_class_id=None) -> bool:
    return user_can_read_class_results(user, school_class_id)


class PromotionPreviewView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_promotion")(),
        ]

    def post(self, request: Request) -> Response:
        if not _can_promote(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        try:
            data = preview_promotion(
                tenant=request.user.tenant,
                user=request.user,
                source_class_id=request.data.get("source_class") or request.data.get("school_class"),
                source_stream_id=request.data.get("source_stream"),
                target_class_id=request.data.get("target_class"),
                target_stream_id=request.data.get("target_stream"),
                target_academic_year_id=request.data.get("target_academic_year"),
                actions=request.data.get("actions") or [],
                notes=request.data.get("notes") or "",
                request=request,
            )
        except PromotionError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "data": data})


class PromotionCommitView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_promotion")(),
        ]

    def post(self, request: Request, batch_id=None) -> Response:
        if not _can_promote(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        issue_certs = bool(
            request.data.get("issue_certificates")
            or request.query_params.get("issue_certificates")
        )
        try:
            data = commit_promotion(
                tenant=request.user.tenant,
                user=request.user,
                batch_id=batch_id or request.data.get("batch_id"),
                request=request,
                issue_certificates=issue_certs,
            )
        except PromotionError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "data": data})


class PromotionUndoView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_promotion")(),
        ]

    def post(self, request: Request, batch_id=None) -> Response:
        if not _can_promote(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        try:
            data = undo_promotion(
                tenant=request.user.tenant,
                user=request.user,
                batch_id=batch_id or request.data.get("batch_id"),
                request=request,
            )
        except PromotionError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "data": data})


class PromotionContextView(APIView):
    """Classes/streams for the promotion wizard."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("student_promotion")(),
        ]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        years = list(
            __import__("apps.academics.models", fromlist=["AcademicYear"]).AcademicYear.objects.filter(
                tenant=tenant, is_deleted=False,
            ).order_by("-start_date").values("id", "name", "is_current", "start_date", "end_date")
        )
        from apps.academics.services.promotion import class_progression_meta

        classes = Class.objects.filter(tenant=tenant, is_deleted=False).select_related("academic_year").order_by("name")
        class_rows = []
        for c in classes:
            streams = list(c.streams.filter(is_deleted=False).values("id", "name"))
            count = Student.objects.filter(tenant=tenant, school_class=c, is_deleted=False, status="active").count()
            prog = class_progression_meta(tenant=tenant, school_class=c)
            class_rows.append({
                "id": str(c.id),
                "name": c.name,
                "code": c.code,
                "level_type": c.level_type or "",
                "academic_year_id": str(c.academic_year_id) if c.academic_year_id else None,
                "academic_year_name": c.academic_year.name if c.academic_year_id else None,
                "streams": [{"id": str(s["id"]), "name": s["name"]} for s in streams],
                "active_students": count,
                "is_terminal": prog["is_terminal"],
                "default_action": prog["default_action"],
                "suggested_next_class_id": prog["suggested_next_class_id"],
                "suggested_next_class_name": prog["suggested_next_class_name"],
                "suggested_next_class_code": prog["suggested_next_class_code"],
            })
        recent = list(
            PromotionBatch.objects.filter(tenant=tenant, is_deleted=False)
            .order_by("-created_at")[:10]
            .values("id", "status", "committed_at", "source_class_id", "preview")
        )
        return Response({
            "success": True,
            "data": {
                "academic_years": [
                    {**y, "id": str(y["id"]), "start_date": str(y["start_date"]), "end_date": str(y["end_date"])}
                    for y in years
                ],
                "classes": class_rows,
                "recent_batches": [
                    {**b, "id": str(b["id"]), "source_class_id": str(b["source_class_id"]) if b["source_class_id"] else None,
                     "committed_at": b["committed_at"].isoformat() if b["committed_at"] else None}
                    for b in recent
                ],
            },
        })


class ReportCardGenerateView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def post(self, request: Request) -> Response:
        class_id = request.data.get("school_class")
        if not _can_print_or_generate_reports(request.user, class_id):
            return Response({
                "success": False,
                "message": "Only the class teacher (for their class) or DoS may generate report cards.",
            }, status=403)
        # Class teachers may set teacher_remarks; DoS may set dos_remarks; subject teachers blocked above
        teacher_remarks = request.data.get("teacher_remarks") or ""
        dos_remarks = request.data.get("dos_remarks") or ""
        principal_remarks = request.data.get("principal_remarks") or ""
        if teacher_remarks and not user_can_edit_class_teacher_remarks(request.user, class_id):
            # DoS/admin may still generate without overwriting class-teacher field unless they head the class
            teacher_remarks = ""
        try:
            data = generate_class_report_cards(
                tenant=request.user.tenant,
                user=request.user,
                term_id=request.data.get("term"),
                school_class_id=class_id,
                stream_id=request.data.get("stream"),
                teacher_remarks=teacher_remarks,
                principal_remarks=principal_remarks if user_is_school_admin(request.user) else "",
                dos_remarks=dos_remarks if results_role_capabilities(request.user).get("is_dos") or user_is_school_admin(request.user) else "",
                request=request,
            )
        except ReportCardError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "data": data})


class ReportCardPublishView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def post(self, request: Request) -> Response:
        class_id = request.data.get("school_class")
        if not _can_print_or_generate_reports(request.user, class_id):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = publish_report_cards(
            tenant=request.user.tenant,
            user=request.user,
            report_card_ids=request.data.get("report_card_ids"),
            term_id=request.data.get("term"),
            school_class_id=class_id,
            stream_id=request.data.get("stream"),
        )
        return Response({"success": True, "data": data, "message": f"Published {data['published']} report card(s)."})


class ReportCardPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def get(self, request: Request, pk=None):
        rc = (
            ReportCard.objects.filter(tenant=request.user.tenant, pk=pk, is_deleted=False)
            .select_related("student", "term", "school_class", "stream", "term__academic_year")
            .prefetch_related("subject_lines")
            .first()
        )
        if not rc:
            return Response({"success": False, "message": "Report card not found."}, status=404)
        if not _can_print_or_generate_reports(request.user, rc.school_class_id):
            return Response({
                "success": False,
                "message": "You may only print report cards for classes you head (or as DoS for any class).",
            }, status=403)
        pdf = build_report_card_pdf(tenant=request.user.tenant, report_card=rc, request=request)
        name = f"report-{rc.student.admission_number}-{rc.term.name}-v{rc.version}.pdf".replace(" ", "-")
        return pdf_attachment_response(pdf_bytes=pdf, filename=name)


class ClassBroadsheetPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("class_report_cards")(),
        ]

    def get(self, request: Request):
        tenant = request.user.tenant
        term_id = request.query_params.get("term")
        class_id = request.query_params.get("school_class")
        stream_id = request.query_params.get("stream")
        if not _can_print_or_generate_reports(request.user, class_id):
            return Response({"success": False, "message": "Permission denied for this class."}, status=403)
        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
        school_class = Class.objects.filter(tenant=tenant, pk=class_id, is_deleted=False).first()
        if not term or not school_class:
            return Response({"success": False, "message": "term and school_class required."}, status=400)
        stream = None
        if stream_id:
            stream = Stream.objects.filter(tenant=tenant, pk=stream_id).first()
        qs = ReportCard.objects.filter(
            tenant=tenant, term=term, school_class=school_class, is_deleted=False, is_latest=True,
        ).select_related("student").prefetch_related("subject_lines").order_by("rank", "student__last_name")
        if stream:
            qs = qs.filter(stream=stream)
        cards = list(qs)
        if not cards:
            return Response({"success": False, "message": "No report cards. Generate first."}, status=404)
        pdf = build_class_broadsheet_pdf(
            tenant=tenant, term=term, school_class=school_class, report_cards=cards, stream=stream, request=request,
        )
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"broadsheet-{school_class.code}-{term.name}.pdf".replace(" ", "-"),
        )


class ReportCardListLatestView(APIView):
    """List latest report cards for a class/term (generation status)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        class_id = request.query_params.get("school_class")
        if class_id and not _can_view_reports(request.user, class_id):
            return Response({"success": False, "message": "Permission denied for this class."}, status=403)
        qs = ReportCard.objects.filter(tenant=tenant, is_deleted=False, is_latest=True).select_related(
            "student", "term", "school_class", "stream",
        )
        # Scope list for non-leadership users
        caps = results_role_capabilities(request.user)
        if not caps.get("can_read_all_classes"):
            allowed = set(caps.get("headed_class_ids") or []) | set(caps.get("taught_class_ids") or [])
            if allowed:
                qs = qs.filter(school_class_id__in=allowed)
            else:
                qs = qs.none()
        if request.query_params.get("term"):
            qs = qs.filter(term_id=request.query_params["term"])
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        if request.query_params.get("stream"):
            qs = qs.filter(stream_id=request.query_params["stream"])
        if request.query_params.get("published") == "1":
            qs = qs.filter(is_published=True)
        if request.query_params.get("published") == "0":
            qs = qs.filter(is_published=False)
        qs = qs.prefetch_related("subject_lines")
        subject_columns: list[dict] = []
        seen_subjects: set[str] = set()
        rows = []
        for rc in qs.order_by("rank", "student__last_name")[:500]:
            subject_scores: dict[str, dict] = {}
            for line in rc.subject_lines.filter(is_deleted=False).order_by("sort_order"):
                key = line.subject_code or line.subject_name
                if key not in seen_subjects:
                    seen_subjects.add(key)
                    subject_columns.append({
                        "key": key,
                        "code": line.subject_code or "",
                        "name": line.subject_name or key,
                    })
                subject_scores[key] = {
                    "total": str(line.total_score) if line.total_score is not None else None,
                    "grade": line.grade or "",
                    "ca": str(line.ca_score) if line.ca_score is not None else None,
                    "exam": str(line.exam_score) if line.exam_score is not None else None,
                }
            rows.append({
                "id": str(rc.id),
                "student_id": str(rc.student_id),
                "student_name": rc.student.full_name if rc.student_id else "",
                "admission_number": rc.student.admission_number if rc.student_id else "",
                "term": rc.term.name if rc.term_id else "",
                "class_name": rc.school_class.name if rc.school_class_id else "",
                "stream_name": rc.stream.name if rc.stream_id else "",
                "average_score": str(rc.average_score),
                "rank": rc.rank,
                "stream_rank": rc.stream_rank,
                "version": rc.version,
                "is_published": rc.is_published,
                "days_present": rc.days_present,
                "days_absent": rc.days_absent,
                "teacher_remarks": rc.teacher_remarks or "",
                "subject_scores": subject_scores,
            })
        return Response({
            "success": True,
            "data": {
                "results": rows,
                "subject_columns": subject_columns,
                "count": len(rows),
                "capabilities": results_role_capabilities(request.user),
            },
        })


class ClassTeacherRemarksView(APIView):
    """
    Bulk set general class-teacher remarks on latest report cards for a class/term.
    Remarks apply per student across the whole card (not per subject score).
    """

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(), IsStaffMember(), TenantActivePermission(),
            RequiresFeature("report_cards")(),
        ]

    def post(self, request: Request) -> Response:
        tenant = request.user.tenant
        class_id = request.data.get("school_class")
        term_id = request.data.get("term")
        remarks_map = request.data.get("remarks") or {}  # { student_id: text } or list
        if not class_id or not term_id:
            return Response({"success": False, "message": "school_class and term are required."}, status=400)
        if not user_can_edit_class_teacher_remarks(request.user, class_id):
            return Response({
                "success": False,
                "message": "Only the class teacher for this class may set class-teacher remarks.",
            }, status=403)

        if isinstance(remarks_map, list):
            remarks_map = {
                str(row.get("student_id") or row.get("student")): (row.get("remarks") or row.get("teacher_remarks") or "")
                for row in remarks_map
            }

        qs = ReportCard.objects.filter(
            tenant=tenant,
            school_class_id=class_id,
            term_id=term_id,
            is_deleted=False,
            is_latest=True,
        )
        updated = 0
        for rc in qs:
            key = str(rc.student_id)
            if key not in remarks_map:
                continue
            text = str(remarks_map[key] or "")[:2000]
            if rc.teacher_remarks != text:
                rc.teacher_remarks = text
                rc.updated_by = request.user
                rc.save(update_fields=["teacher_remarks", "updated_by", "updated_at"])
                updated += 1
        return Response({
            "success": True,
            "message": f"Updated class-teacher remarks for {updated} student(s).",
            "data": {"updated": updated},
        })


class ResultsCapabilitiesView(APIView):
    """Role capabilities for marks / results / report-card workspaces."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get(self, request: Request) -> Response:
        from apps.examinations.marks_scoping import marks_scope_meta

        tenant = request.user.tenant
        return Response({
            "success": True,
            "data": {
                **results_role_capabilities(request.user),
                "scope_meta": marks_scope_meta(tenant, request.user) if tenant else {},
            },
        })


class ClassResultsOverviewView(APIView):
    """
    Read-only class results matrix for a term.

    Visibility:
    - Class teachers / DoS / leadership: all subjects and statuses for in-scope classes.
    - Subject teachers: own subjects at any marks status; other subjects only when
      marks are approved or locked. Never write outside teaching pairs (this view is read-only).

    Response includes per-subject totals and student average as separate columns.
    """

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresFeature("result_processing")(),
        ]

    def get(self, request: Request) -> Response:
        from decimal import Decimal, InvalidOperation
        from uuid import UUID

        from apps.academics.scoping import get_academic_context
        from apps.examinations.constants import (
            MARKS_STATUS_APPROVED,
            MARKS_STATUS_LOCKED,
        )
        from apps.examinations.models import Exam, Grade

        tenant = request.user.tenant
        term_id = request.query_params.get("term")
        class_id = request.query_params.get("school_class")
        stream_id = request.query_params.get("stream")

        if not term_id or not class_id:
            return Response(
                {"success": False, "message": "term and school_class are required."},
                status=400,
            )
        if not user_can_read_class_results(request.user, class_id):
            return Response(
                {"success": False, "message": "You may only view results for classes in your scope."},
                status=403,
            )

        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
        school_class = Class.objects.filter(tenant=tenant, pk=class_id, is_deleted=False).first()
        if not term or not school_class:
            return Response({"success": False, "message": "Term or class not found."}, status=404)

        students_qs = Student.objects.filter(
            tenant=tenant,
            school_class_id=class_id,
            status="active",
            is_deleted=False,
        ).order_by("last_name", "first_name")
        if stream_id:
            students_qs = students_qs.filter(stream_id=stream_id)
        students = list(students_qs)

        exam_qs = Exam.objects.filter(
            tenant=tenant,
            term_id=term_id,
            school_class_id=class_id,
            is_deleted=False,
        ).exclude(exam_type="assignment").select_related("subject", "paper")

        caps = results_role_capabilities(request.user)
        ctx = get_academic_context(request.user)
        try:
            cid = UUID(str(class_id))
        except (TypeError, ValueError):
            cid = None

        headed = set(ctx.class_teacher_class_ids) if ctx else set()
        is_heading = cid is not None and cid in headed
        can_see_all_statuses = bool(caps.get("can_read_all_classes") or is_heading)

        own_subject_ids: set = set()
        if ctx and ctx.teaching_pairs and cid is not None:
            own_subject_ids = {sid for sid, clid in ctx.teaching_pairs if clid == cid}

        all_exams = list(exam_qs.order_by("subject__name", "paper__sort_order", "name"))
        approved_statuses = {MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED}

        visible_exams = []
        for exam in all_exams:
            if can_see_all_statuses:
                visible_exams.append(exam)
                continue
            if exam.subject_id in own_subject_ids:
                visible_exams.append(exam)
                continue
            # Other subjects: only once marks are approved/locked
            if exam.marks_status in approved_statuses:
                visible_exams.append(exam)

        exams = visible_exams
        subjects_map: dict[str, dict] = {}
        for exam in exams:
            sid = str(exam.subject_id)
            if sid not in subjects_map:
                subjects_map[sid] = {
                    "id": sid,
                    "name": exam.subject.name if exam.subject_id else "",
                    "code": exam.subject.code if exam.subject_id else "",
                    "exams": [],
                    "can_edit": exam.subject_id in own_subject_ids,
                    "is_own_subject": exam.subject_id in own_subject_ids,
                }
            subjects_map[sid]["exams"].append({
                "id": str(exam.id),
                "name": exam.name,
                "paper": exam.paper.code if exam.paper_id else "",
                "max_score": str(exam.max_score),
                "marks_status": exam.marks_status,
                "can_edit": exam.subject_id in own_subject_ids,
            })
            # can_edit true if any owned exam for subject
            if exam.subject_id in own_subject_ids:
                subjects_map[sid]["can_edit"] = True
                subjects_map[sid]["is_own_subject"] = True

        grade_rows = Grade.objects.filter(
            tenant=tenant,
            exam_id__in=[e.id for e in exams],
            is_deleted=False,
        ).select_related("student", "exam")
        cells: dict[str, dict[str, dict]] = {}
        for g in grade_rows:
            sid = str(g.student_id)
            eid = str(g.exam_id)
            cells.setdefault(sid, {})[eid] = {
                "score": str(g.score) if g.score is not None else "",
                "grade": g.grade or "",
                "remarks": g.remarks or "",
            }

        def _to_decimal(value) -> Decimal | None:
            if value in (None, ""):
                return None
            try:
                return Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                return None

        student_rows = []
        for s in students:
            student_marks = cells.get(str(s.id), {})
            subject_totals: dict[str, dict] = {}
            subject_scores: list[Decimal] = []
            for subject in subjects_map.values():
                scores: list[Decimal] = []
                grades_seen: list[str] = []
                statuses: list[str] = []
                for exam in subject["exams"]:
                    cell = student_marks.get(exam["id"])
                    if not cell:
                        continue
                    score = _to_decimal(cell.get("score"))
                    if score is not None:
                        scores.append(score)
                    if cell.get("grade"):
                        grades_seen.append(cell["grade"])
                    statuses.append(exam.get("marks_status") or "")
                if not scores:
                    subject_totals[subject["id"]] = {
                        "score": None,
                        "grade": "",
                        "marks_status": statuses[-1] if statuses else "",
                        "exam_count": len(subject["exams"]),
                        "scored_count": 0,
                    }
                    continue
                avg = sum(scores) / Decimal(len(scores))
                avg = avg.quantize(Decimal("0.01"))
                subject_scores.append(avg)
                subject_totals[subject["id"]] = {
                    "score": str(avg),
                    "grade": grades_seen[-1] if grades_seen else "",
                    "marks_status": statuses[-1] if statuses else "",
                    "exam_count": len(subject["exams"]),
                    "scored_count": len(scores),
                }

            average = None
            if subject_scores:
                average = (sum(subject_scores) / Decimal(len(subject_scores))).quantize(Decimal("0.01"))

            student_rows.append({
                "id": str(s.id),
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "stream_id": str(s.stream_id) if s.stream_id else None,
                "marks": student_marks,
                "subject_totals": subject_totals,
                "average": str(average) if average is not None else None,
            })

        return Response({
            "success": True,
            "data": {
                "term": {"id": str(term.id), "name": term.name},
                "school_class": {
                    "id": str(school_class.id),
                    "name": school_class.name,
                    "code": school_class.code,
                },
                "subjects": list(subjects_map.values()),
                "students": student_rows,
                "exam_count": len(exams),
                "student_count": len(student_rows),
                "capabilities": caps,
                "own_subject_ids": [str(x) for x in own_subject_ids],
                "view_mode": "class_matrix",
                "read_only": True,
                "visibility": {
                    "sees_all_statuses": can_see_all_statuses,
                    "approved_only_for_other_subjects": not can_see_all_statuses,
                },
            },
        })
