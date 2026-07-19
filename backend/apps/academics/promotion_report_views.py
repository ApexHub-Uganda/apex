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


def _can_manage_reports(user) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = user.tenant
    if tenant is None:
        return False
    return (
        user_can_access_feature(tenant, user, "report_cards", require_write=True)
        or user_can_access_feature(tenant, user, "class_report_cards", require_write=True)
        or user_can_access_feature(tenant, user, "result_processing", require_write=True)
        or user_can_access_feature(tenant, user, "dos_workspace", require_write=True)
    )


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
        if not _can_manage_reports(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        try:
            data = generate_class_report_cards(
                tenant=request.user.tenant,
                user=request.user,
                term_id=request.data.get("term"),
                school_class_id=request.data.get("school_class"),
                stream_id=request.data.get("stream"),
                teacher_remarks=request.data.get("teacher_remarks") or "",
                principal_remarks=request.data.get("principal_remarks") or "",
                dos_remarks=request.data.get("dos_remarks") or "",
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
        if not _can_manage_reports(request.user):
            return Response({"success": False, "message": "Permission denied."}, status=403)
        data = publish_report_cards(
            tenant=request.user.tenant,
            user=request.user,
            report_card_ids=request.data.get("report_card_ids"),
            term_id=request.data.get("term"),
            school_class_id=request.data.get("school_class"),
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
        qs = ReportCard.objects.filter(tenant=tenant, is_deleted=False, is_latest=True).select_related(
            "student", "term", "school_class", "stream",
        )
        if request.query_params.get("term"):
            qs = qs.filter(term_id=request.query_params["term"])
        if request.query_params.get("school_class"):
            qs = qs.filter(school_class_id=request.query_params["school_class"])
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
            })
        return Response({"success": True, "data": {"results": rows, "count": len(rows)}})
