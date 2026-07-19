"""Examination timetable API — same submodule as lesson builder."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.academics.services.exam_timetable import (
    build_exam_timetable_pdf,
    build_exam_wizard_context,
    create_draft_exam_schedule,
    get_exam_schedule_slots,
    publish_exam_schedule,
    save_exam_slots,
    validate_exam_slots,
)
from apps.academics.timetable_generator import assert_timetable_write, serialize_schedule
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission


class ExamTimetableContextView(APIView):
    """Classes, subjects, free-pick teachers, sessions, published busy hints."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        data = build_exam_wizard_context(tenant=tenant, user=request.user)
        return Response({"success": True, "data": data})


class ExamTimetableCreateDraftView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        try:
            schedule = create_draft_exam_schedule(
                tenant=request.user.tenant,
                user=request.user,
                examination_session_id=request.data.get("examination_session")
                or request.data.get("examination_session_id"),
                term_id=request.data.get("term"),
                name=request.data.get("name") or "",
            )
        except DRFValidationError as exc:
            detail = exc.detail
            msg = detail if isinstance(detail, str) else str(detail)
            return Response({"success": False, "message": msg}, status=400)
        return Response({
            "success": True,
            "data": serialize_schedule(schedule, user=request.user),
            "message": "Exam timetable draft created.",
        }, status=status.HTTP_201_CREATED)


class ExamTimetableSlotsView(APIView):
    """GET slots for a schedule / POST save full slot list."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        schedule_id = request.query_params.get("schedule") or request.query_params.get("schedule_id")
        if not schedule_id:
            return Response({"success": False, "message": "schedule is required."}, status=400)
        try:
            data = get_exam_schedule_slots(tenant=request.user.tenant, schedule_id=schedule_id)
        except DRFValidationError as exc:
            return Response({"success": False, "message": str(exc.detail)}, status=400)
        return Response({"success": True, "data": data})

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        schedule_id = request.data.get("schedule_id") or request.data.get("schedule")
        if not schedule_id:
            return Response({"success": False, "message": "schedule_id is required."}, status=400)
        try:
            data = save_exam_slots(
                tenant=request.user.tenant,
                user=request.user,
                schedule_id=schedule_id,
                slots=request.data.get("slots") or [],
                force=bool(request.data.get("force")),
            )
        except DRFValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict) and "conflicts" in detail:
                return Response({
                    "success": False,
                    "message": detail.get("detail") or "Conflicts detected.",
                    "conflicts": detail.get("conflicts"),
                    "code": "conflicts",
                }, status=400)
            msg = detail if isinstance(detail, str) else (
                detail.get("detail") if isinstance(detail, dict) else str(detail)
            )
            return Response({"success": False, "message": msg or "Save failed.", "errors": detail}, status=400)
        return Response({
            "success": True,
            "data": data,
            "message": f"Saved {data.get('entries_created', 0)} exam sitting(s).",
        })


class ExamTimetableValidateView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        data = validate_exam_slots(
            tenant=request.user.tenant,
            slots=request.data.get("slots") or [],
            schedule_id=request.data.get("schedule_id") or request.data.get("schedule"),
        )
        return Response({"success": True, "data": data})


class ExamTimetablePublishView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        schedule_id = request.data.get("schedule_id") or request.data.get("schedule")
        if not schedule_id:
            return Response({"success": False, "message": "schedule_id is required."}, status=400)
        try:
            data = publish_exam_schedule(
                tenant=request.user.tenant,
                user=request.user,
                schedule_id=schedule_id,
            )
        except DRFValidationError as exc:
            detail = exc.detail
            msg = detail if isinstance(detail, str) else str(detail)
            return Response({"success": False, "message": msg}, status=400)
        return Response({
            "success": True,
            "data": data,
            "message": "Exam timetable published. Teachers can view and download it.",
        })


class ExamTimetablePrintPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request):
        schedule_id = request.query_params.get("schedule") or request.query_params.get("schedule_id")
        if not schedule_id:
            return Response({"success": False, "message": "schedule is required."}, status=400)
        orientation = (request.query_params.get("orientation") or "landscape").lower()
        teacher_mode = (
            request.query_params.get("teacher_mode")
            or request.query_params.get("mine_mode")
            or ""
        ).strip().lower()
        teacher_id = request.query_params.get("teacher_id") or request.query_params.get("teacher")
        try:
            pdf = build_exam_timetable_pdf(
                tenant=request.user.tenant,
                schedule_id=schedule_id,
                orientation=orientation,
                request=request,
                teacher_mode=teacher_mode or None,
                teacher_id=teacher_id or None,
            )
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        suffix = f"-{teacher_mode}" if teacher_mode in ("highlight", "mine_only") else ""
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"exam-timetable{suffix}-{orientation}.pdf",
        )
