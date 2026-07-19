"""API for timetable generation wizard and schedules."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Timetable, TimetableGenerationDraft, TimetableSchedule
from apps.academics.serializers import TimetableScheduleSerializer, TimetableSerializer
from apps.academics.timetable_generator import (
    apply_generation_draft,
    assert_timetable_admin_lock,
    assert_timetable_write,
    build_generation_context,
    create_generation_draft,
    regenerate_draft,
    schedule_is_locked_for_user,
    serialize_draft,
    serialize_schedule,
)
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.tenants.role_permissions import user_is_school_admin


class TimetableGenerationContextView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        return Response({"success": True, "data": build_generation_context(tenant)})


class TimetableGenerateView(APIView):
    """Create a generation draft (or regenerate with new seed)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def post(self, request: Request) -> Response:
        assert_timetable_write(request.user)
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        draft_id = request.data.get("draft_id")
        if draft_id:
            draft = TimetableGenerationDraft.objects.filter(
                tenant=tenant, id=draft_id, is_deleted=False,
            ).first()
            if draft is None:
                return Response(
                    {"success": False, "message": "Draft not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            draft = regenerate_draft(draft=draft, user=request.user)
        else:
            draft = create_generation_draft(
                tenant=tenant,
                user=request.user,
                schedule_type=request.data.get("schedule_type") or "lesson",
                config=request.data.get("config") or request.data,
                seed=request.data.get("seed"),
            )
        return Response({
            "success": True,
            "message": "Timetable draft generated. Review, regenerate, or use it.",
            "data": serialize_draft(draft),
        }, status=status.HTTP_201_CREATED)


class TimetableDraftDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]

    def get(self, request: Request, draft_id: str) -> Response:
        tenant = request.user.tenant
        draft = TimetableGenerationDraft.objects.filter(
            tenant=tenant, id=draft_id, is_deleted=False,
        ).first()
        if draft is None:
            return Response({"success": False, "message": "Draft not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "data": serialize_draft(draft)})

    def post(self, request: Request, draft_id: str) -> Response:
        """Apply draft — USE IT."""
        assert_timetable_write(request.user)
        tenant = request.user.tenant
        draft = TimetableGenerationDraft.objects.filter(
            tenant=tenant, id=draft_id, is_deleted=False,
        ).first()
        if draft is None:
            return Response({"success": False, "message": "Draft not found."}, status=status.HTTP_404_NOT_FOUND)
        action_name = (request.data.get("action") or "apply").lower()
        if action_name == "regenerate":
            draft = regenerate_draft(draft=draft, user=request.user)
            return Response({
                "success": True,
                "message": "Timetable reshuffled.",
                "data": serialize_draft(draft),
            })
        schedule = apply_generation_draft(draft=draft, user=request.user)
        return Response({
            "success": True,
            "message": "Timetable applied and locked for this term/session. School admins can still edit if needed.",
            "data": serialize_schedule(schedule),
        })


class TimetableScheduleViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "delete", "head", "options"]
    serializer_class = TimetableScheduleSerializer
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission, RequiresFeature("timetables")]
    filterset_fields = ["schedule_type", "status", "term", "examination_session"]
    search_fields = ["name"]

    def get_queryset(self):
        user = self.request.user
        qs = TimetableSchedule.objects.filter(is_deleted=False).select_related(
            "term", "examination_session", "academic_year", "applied_by",
            "created_by", "published_by",
        )
        if user_is_school_admin(user) and not user.tenant_id:
            return qs
        qs = qs.filter(tenant=user.tenant)
        # Teachers / non-writers only see published schedules
        from apps.tenants.role_permissions import user_can_access_feature
        can_write = user_is_school_admin(user) or user_can_access_feature(
            user.tenant, user, "timetables", require_write=True,
        )
        if not can_write:
            qs = qs.filter(status__in=[
                TimetableSchedule.STATUS_PUBLISHED,
                TimetableSchedule.STATUS_ACTIVE,
            ])
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset()).order_by("-updated_at", "-created_at")
        data = [serialize_schedule(s, user=request.user) for s in qs[:50]]
        drafts = [d for d in data if d["status"] == "draft"]
        published = [d for d in data if d.get("is_published")]
        return Response({
            "success": True,
            "data": data,
            "count": len(data),
            "summary": {
                "total": len(data),
                "drafts": len(drafts),
                "published": len(published),
            },
        })

    def retrieve(self, request, *args, **kwargs):
        schedule = self.get_object()
        # Non-writers may only retrieve published schedules
        if not schedule.is_published:
            from apps.tenants.role_permissions import user_can_access_feature
            can_write = user_is_school_admin(request.user) or user_can_access_feature(
                request.user.tenant, request.user, "timetables", require_write=True,
            )
            if not can_write:
                return Response(
                    {"success": False, "message": "This timetable is not published."},
                    status=403,
                )
        payload = serialize_schedule(schedule, user=request.user)
        entries = Timetable.objects.filter(
            schedule=schedule, is_deleted=False,
        ).select_related(
            "school_class", "subject", "teacher__staff", "period", "stream",
        ).order_by("school_class__name", "day_of_week", "start_time", "stream__name")
        payload["entries"] = TimetableSerializer(entries, many=True).data
        # Compact class-grouped preview for UI
        by_class: dict = {}
        for e in entries:
            ck = str(e.school_class_id)
            if ck not in by_class:
                by_class[ck] = {
                    "school_class_id": ck,
                    "school_class_name": e.school_class.name if e.school_class_id else "",
                    "slots": [],
                }
            by_class[ck]["slots"].append({
                "day_of_week": e.day_of_week,
                "day_label": dict(enumerate(
                    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                )).get(e.day_of_week, ""),
                "exam_date": str(e.exam_date) if e.exam_date else None,
                "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
                "end_time": e.end_time.strftime("%H:%M") if e.end_time else "",
                "period_name": e.period.name if e.period_id else "",
                "stream_name": e.stream.name if e.stream_id else "",
                "room": e.room or "",
                "is_break": e.is_break_slot,
                "subject": e.display_subject or (e.subject.name if e.subject_id else e.slot_label or ""),
                "teacher_id": str(e.teacher_id) if e.teacher_id else None,
                "teacher": e.display_teacher or (
                    e.teacher.staff.full_name if e.teacher_id and getattr(e.teacher, "staff_id", None) else ""
                ),
            })
        payload["preview_by_class"] = list(by_class.values())
        from apps.academics.scoping import get_teacher_for_user
        from apps.academics.services.timetable_builder import _teacher_name
        viewer = get_teacher_for_user(request.user)
        payload["viewer_teacher_id"] = str(viewer.id) if viewer else None
        payload["viewer_teacher_name"] = _teacher_name(viewer) if viewer else ""
        return Response({"success": True, "data": payload})

    def destroy(self, request, *args, **kwargs):
        schedule = self.get_object()
        if schedule.is_published or schedule.is_locked or schedule.status in (
            TimetableSchedule.STATUS_ACTIVE, TimetableSchedule.STATUS_PUBLISHED,
        ):
            assert_timetable_admin_lock(request.user)
        schedule.status = TimetableSchedule.STATUS_ARCHIVED
        schedule.is_deleted = True
        schedule.updated_by = request.user
        schedule.save(update_fields=["status", "is_deleted", "updated_by", "updated_at"])
        Timetable.objects.filter(schedule=schedule, is_deleted=False).update(
            is_deleted=True, updated_by=request.user,
        )
        return Response({"success": True, "message": "Timetable schedule deleted."})

    @action(detail=True, methods=["get"], url_path="grid")
    def grid(self, request: Request, pk=None) -> Response:
        schedule = self.get_object()
        entries = Timetable.objects.filter(
            schedule=schedule, is_deleted=False,
        ).select_related("school_class", "subject", "teacher__staff", "period", "stream")
        grid: dict[str, list] = {}
        for entry in entries:
            key = str(entry.school_class_id)
            grid.setdefault(key, []).append(TimetableSerializer(entry).data)
        return Response({
            "success": True,
            "data": {
                "schedule": serialize_schedule(schedule),
                "by_class": grid,
            },
        })
