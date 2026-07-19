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
        )
        if user_is_school_admin(user) and not user.tenant_id:
            return qs
        return qs.filter(tenant=user.tenant)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        data = [serialize_schedule(s) for s in qs[:50]]
        return Response({"success": True, "data": data, "count": len(data)})

    def retrieve(self, request, *args, **kwargs):
        schedule = self.get_object()
        payload = serialize_schedule(schedule)
        entries = Timetable.objects.filter(
            schedule=schedule, is_deleted=False,
        ).select_related("school_class", "subject", "teacher__staff", "period", "stream")
        payload["entries"] = TimetableSerializer(entries, many=True).data
        return Response({"success": True, "data": payload})

    def destroy(self, request, *args, **kwargs):
        schedule = self.get_object()
        if schedule.is_locked or schedule.status == TimetableSchedule.STATUS_ACTIVE:
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
