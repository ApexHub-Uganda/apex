"""Class-by-class timetable grid API + print."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.academics.services.timetable_builder import (
    build_wizard_context,
    bulk_sync_periods,
    create_draft_schedule,
    get_class_grid,
    publish_timetable_schedule,
    resolve_default_teacher,
    save_class_grid,
    serialize_period,
    unpublish_timetable_schedule,
    validate_grid_cells,
)
from apps.academics.timetable_generator import serialize_schedule
from apps.academics.services.timetable_pdf import build_timetable_pdf
from apps.academics.timetable_generator import assert_timetable_write, build_generation_context
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission


class TimetableWizardContextView(APIView):
    """Unified wizard context (periods, classes, assignments, readiness)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        data = build_wizard_context(tenant=tenant, user=request.user)
        # Keep auto-generator readiness available without breaking old clients
        try:
            data["auto_generate"] = build_generation_context(tenant)
        except Exception:
            data["auto_generate"] = None
        return Response({"success": True, "data": data})


class TimetablePeriodsSyncView(APIView):
    """Create/update the shared school period bell schedule (from/to for all days)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        tenant = request.user.tenant
        periods = request.data.get("periods") or []
        try:
            result = bulk_sync_periods(tenant=tenant, user=request.user, periods_payload=periods)
        except DRFValidationError as exc:
            detail = exc.detail
            # Prefer a plain string message for the UI toast
            if isinstance(detail, list) and detail:
                message = str(detail[0])
            elif isinstance(detail, dict):
                # Flatten {"periods": "..."} or non_field_errors
                parts = []
                for v in detail.values():
                    if isinstance(v, list):
                        parts.extend(str(x) for x in v)
                    else:
                        parts.append(str(v))
                message = "; ".join(parts) if parts else "Invalid periods."
            else:
                message = str(detail) if detail else "Invalid periods."
            return Response({"success": False, "message": message, "errors": detail}, status=400)
        except Exception as exc:  # noqa: BLE001 — surface DB uniqueness etc. clearly
            return Response(
                {"success": False, "message": str(exc) or "Could not save periods."},
                status=400,
            )
        return Response({
            "success": True,
            "data": {"periods": [serialize_period(p) for p in result]},
            "message": f"Saved {len(result)} period(s). Times apply Mon–Sun.",
        })


class TimetableClassGridView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        class_id = request.query_params.get("school_class")
        if not class_id:
            return Response({"success": False, "message": "school_class is required."}, status=400)
        days = request.query_params.getlist("day") or request.query_params.get("days")
        working_days = None
        if days:
            if isinstance(days, str):
                working_days = [int(x) for x in days.split(",") if x.strip() != ""]
            else:
                working_days = [int(x) for x in days]
        try:
            data = get_class_grid(
                tenant=tenant,
                school_class_id=class_id,
                term_id=request.query_params.get("term"),
                stream_id=request.query_params.get("stream"),
                working_days=working_days,
            )
        except DRFValidationError as exc:
            return Response({"success": False, "message": "Unable to load grid.", "errors": exc.detail}, status=400)
        return Response({"success": True, "data": data})

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        tenant = request.user.tenant
        try:
            data = save_class_grid(
                tenant=tenant,
                user=request.user,
                school_class_id=request.data.get("school_class"),
                term_id=request.data.get("term"),
                stream_id=request.data.get("stream"),
                cells=request.data.get("cells") or [],
                working_days=request.data.get("working_days"),
                schedule_name=request.data.get("name") or "",
                schedule_id=request.data.get("schedule_id") or request.data.get("schedule"),
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
        return Response({"success": True, "data": data, "message": "Class timetable saved."})


class TimetableCreateDraftView(APIView):
    """Create an empty draft schedule so it appears immediately in the library."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        try:
            schedule = create_draft_schedule(
                tenant=request.user.tenant,
                user=request.user,
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
            "message": "Draft timetable created.",
        }, status=201)


class TimetableValidateGridView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        tenant = request.user.tenant
        data = validate_grid_cells(
            tenant=tenant,
            school_class_id=request.data.get("school_class"),
            term_id=request.data.get("term"),
            cells=request.data.get("cells") or [],
            stream_id=request.data.get("stream"),
        )
        return Response({"success": True, "data": data})


class TimetableDefaultTeacherView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        result = resolve_default_teacher(
            tenant=tenant,
            school_class_id=request.query_params.get("school_class"),
            subject_id=request.query_params.get("subject"),
        )
        return Response({"success": True, "data": result})


class TimetablePublishView(APIView):
    """Publish draft timetable so teachers can read/download it."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        try:
            data = publish_timetable_schedule(
                tenant=request.user.tenant,
                user=request.user,
                term_id=request.data.get("term"),
                schedule_id=request.data.get("schedule_id") or request.data.get("schedule"),
            )
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            if isinstance(exc, DRFValidationError):
                detail = exc.detail
                msg = detail if isinstance(detail, str) else str(detail)
                return Response({"success": False, "message": msg}, status=400)
            return Response({"success": False, "message": str(exc)}, status=400)
        return Response({
            "success": True,
            "data": data,
            "message": "Timetable published. Teachers can now view and download it.",
        })


class TimetableUnpublishView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        try:
            data = unpublish_timetable_schedule(
                tenant=request.user.tenant,
                user=request.user,
                schedule_id=request.data.get("schedule_id") or request.data.get("schedule"),
            )
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        return Response({"success": True, "data": data, "message": "Timetable returned to draft."})


class TimetablePrintPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request):
        tenant = request.user.tenant
        class_ids = request.query_params.getlist("school_class") or []
        if not class_ids and request.query_params.get("school_classes"):
            class_ids = [x for x in request.query_params.get("school_classes").split(",") if x]
        orientation = (request.query_params.get("orientation") or "landscape").lower()
        days_raw = request.query_params.get("days")
        working_days = None
        if days_raw:
            working_days = [int(x) for x in days_raw.split(",") if x.strip() != ""]
        schedule_id = request.query_params.get("schedule") or request.query_params.get("schedule_id")
        teacher_mode = (
            request.query_params.get("teacher_mode")
            or request.query_params.get("mine_mode")
            or ""
        ).strip().lower()
        teacher_id = request.query_params.get("teacher_id") or request.query_params.get("teacher")

        # Route exam schedules to the exam PDF builder (date + invigilator + QR)
        if schedule_id:
            from apps.academics.models import TimetableSchedule
            sched = TimetableSchedule.objects.filter(
                tenant=tenant, pk=schedule_id, is_deleted=False,
            ).only("id", "schedule_type", "name").first()
            if sched and sched.schedule_type == TimetableSchedule.SCHEDULE_EXAM:
                from apps.academics.services.exam_timetable import build_exam_timetable_pdf
                try:
                    pdf = build_exam_timetable_pdf(
                        tenant=tenant,
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

        try:
            pdf = build_timetable_pdf(
                tenant=tenant,
                term_id=request.query_params.get("term"),
                class_ids=class_ids or None,
                orientation=orientation,
                working_days=working_days,
                schedule_id=schedule_id,
                request=request,
                teacher_mode=teacher_mode or None,
                teacher_id=teacher_id or None,
            )
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        scope = "school" if not class_ids else ("class" if len(class_ids) == 1 else "classes")
        suffix = f"-{teacher_mode}" if teacher_mode in ("highlight", "mine_only") else ""
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"timetable-{scope}{suffix}-{orientation}.pdf",
        )
