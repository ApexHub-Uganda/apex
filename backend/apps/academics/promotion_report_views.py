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
        try:
            data = commit_promotion(
                tenant=request.user.tenant,
                user=request.user,
                batch_id=batch_id or request.data.get("batch_id"),
                request=request,
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
        classes = Class.objects.filter(tenant=tenant, is_deleted=False).select_related("academic_year").order_by("name")
        class_rows = []
        for c in classes:
            streams = list(c.streams.filter(is_deleted=False).values("id", "name"))
            count = Student.objects.filter(tenant=tenant, school_class=c, is_deleted=False, status="active").count()
            class_rows.append({
                "id": str(c.id),
                "name": c.name,
                "code": c.code,
                "academic_year_id": str(c.academic_year_id) if c.academic_year_id else None,
                "academic_year_name": c.academic_year.name if c.academic_year_id else None,
                "streams": [{"id": str(s["id"]), "name": s["name"]} for s in streams],
                "active_students": count,
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
        rows = []
        for rc in qs.order_by("rank", "student__last_name")[:500]:
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
            })
        return Response({
            "success": True,
            "data": {
                "results": rows,
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

    - Subject teachers: only subjects they teach in that class.
    - Class teachers: all subjects for headed classes.
    - DoS / leadership: all subjects for any class.
    Does not allow mark edits or report-card generation.
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
        from apps.academics.scoping import get_academic_context
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

        # Narrow subject teachers to their teaching pairs for this class
        caps = results_role_capabilities(request.user)
        if not caps.get("can_read_all_classes"):
            ctx = get_academic_context(request.user)
            headed = set(ctx.class_teacher_class_ids) if ctx else set()
            try:
                from uuid import UUID
                cid = UUID(str(class_id))
            except (TypeError, ValueError):
                cid = None
            is_heading = cid is not None and cid in headed
            if not is_heading and ctx and ctx.teaching_pairs:
                allowed_subjects = {
                    sid for sid, clid in ctx.teaching_pairs if clid == cid
                }
                exam_qs = exam_qs.filter(subject_id__in=allowed_subjects)
            elif not is_heading and not (ctx and ctx.teaching_pairs):
                exam_qs = exam_qs.none()

        exams = list(exam_qs.order_by("subject__name", "paper__sort_order", "name"))
        subjects_map: dict[str, dict] = {}
        for exam in exams:
            sid = str(exam.subject_id)
            if sid not in subjects_map:
                subjects_map[sid] = {
                    "id": sid,
                    "name": exam.subject.name if exam.subject_id else "",
                    "code": exam.subject.code if exam.subject_id else "",
                    "exams": [],
                }
            subjects_map[sid]["exams"].append({
                "id": str(exam.id),
                "name": exam.name,
                "paper": exam.paper.code if exam.paper_id else "",
                "max_score": str(exam.max_score),
                "marks_status": exam.marks_status,
            })

        grade_rows = Grade.objects.filter(
            tenant=tenant,
            exam_id__in=[e.id for e in exams],
            is_deleted=False,
        ).select_related("student", "exam")
        # cell: student_id -> exam_id -> {score, grade, remarks}
        cells: dict[str, dict[str, dict]] = {}
        for g in grade_rows:
            sid = str(g.student_id)
            eid = str(g.exam_id)
            cells.setdefault(sid, {})[eid] = {
                "score": str(g.score),
                "grade": g.grade or "",
                "remarks": g.remarks or "",
            }

        student_rows = []
        for s in students:
            student_rows.append({
                "id": str(s.id),
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "stream_id": str(s.stream_id) if s.stream_id else None,
                "marks": cells.get(str(s.id), {}),
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
                "read_only": True,
            },
        })
