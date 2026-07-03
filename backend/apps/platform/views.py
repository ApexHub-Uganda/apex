"""Platform super-admin views."""
from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSuperAdmin
from apps.platform.models import (
    APIKey,
    CallSetting,
    EmailSetting,
    GlobalSetting,
    PlanAdvertisement,
    PlatformBroadcast,
    PlatformNews,
    PlatformNotification,
    SMSSetting,
    SystemHealthLog,
)
from apps.platform.serializers import (
    APIKeySerializer,
    CallSettingSerializer,
    EmailSettingSerializer,
    GlobalSettingSerializer,
    PlanAdvertisementSerializer,
    PlatformBroadcastSerializer,
    PlatformNewsSerializer,
    PlatformNotificationSerializer,
    PlatformSettingsSerializer,
    SMSSettingSerializer,
    SystemHealthLogSerializer,
)
from apps.platform.services.plan_advertisements import (
    PLAN_ORDER,
    build_default_advertisement_payload,
    broadcast_plan_advertisement,
    get_plan_label,
    get_upgrade_options,
)
from apps.platform.services.notification_feed import (
    get_platform_notification_summary,
    mark_all_platform_notifications_read,
    mark_platform_notification_read,
)
from apps.platform.services.notifications import approve_school_registration, get_pending_registration_count
from apps.tenants.models import Tenant
from apps.tenants.serializers import TenantSerializer


class GlobalSettingViewSet(viewsets.ModelViewSet):
    queryset = GlobalSetting.objects.all()
    serializer_class = GlobalSettingSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = "key"


class EmailSettingViewSet(viewsets.ModelViewSet):
    queryset = EmailSetting.objects.all()
    serializer_class = EmailSettingSerializer
    permission_classes = [IsSuperAdmin]


class SMSSettingViewSet(viewsets.ModelViewSet):
    queryset = SMSSetting.objects.all()
    serializer_class = SMSSettingSerializer
    permission_classes = [IsSuperAdmin]


class CallSettingViewSet(viewsets.ModelViewSet):
    queryset = CallSetting.objects.all()
    serializer_class = CallSettingSerializer
    permission_classes = [IsSuperAdmin]


class PlatformNotificationViewSet(viewsets.ModelViewSet):
    """Super-admin notifications and actionable to-do items."""

    serializer_class = PlatformNotificationSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["status", "notification_type", "priority", "is_read", "tenant"]
    search_fields = ["title", "message", "tenant__name", "tenant__code"]
    ordering_fields = ["created_at", "priority", "status"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        from apps.platform.services.notification_feed import platform_notifications_queryset_for_user

        return platform_notifications_queryset_for_user(self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        data = get_platform_notification_summary(request.user)
        data["pending_count"] = get_pending_registration_count()
        recent_full = self.get_queryset().filter(status="pending")[:5]
        data["recent_full"] = PlatformNotificationSerializer(recent_full, many=True).data
        return Response({"success": True, "data": data})

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str = None) -> Response:
        notification = self.get_object()
        tenant = notification.tenant
        approve_school_registration(tenant, actor=request.user)
        mark_platform_notification_read(notification, request.user)
        notification.refresh_from_db()
        return Response({
            "success": True,
            "message": f"{tenant.name} has been approved.",
            "data": PlatformNotificationSerializer(notification).data,
        })

    @action(detail=True, methods=["post"])
    def dismiss(self, request: Request, pk: str = None) -> Response:
        notification = self.get_object()
        notification.status = "dismissed"
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.action_taken_by = request.user
        notification.action_taken_at = timezone.now()
        notification.save()
        mark_platform_notification_read(notification, request.user)
        return Response({
            "success": True,
            "message": "Notification dismissed.",
            "data": PlatformNotificationSerializer(notification).data,
        })

    @action(detail=True, methods=["post"])
    def mark_read(self, request: Request, pk: str = None) -> Response:
        notification = self.get_object()
        mark_platform_notification_read(notification, request.user)
        return Response({"success": True, "data": PlatformNotificationSerializer(notification).data})

    @action(detail=True, methods=["post"])
    def delete_notification(self, request: Request, pk: str = None) -> Response:
        from apps.platform.services.notification_feed import hide_platform_notification

        notification = self.get_object()
        hide_platform_notification(notification, request.user)
        return Response({"success": True, "message": "Notification removed from your inbox."})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request: Request) -> Response:
        count = mark_all_platform_notifications_read(request.user)
        return Response({"success": True, "message": f"{count} notifications marked as read."})

    @action(detail=False, methods=["post"])
    def delete_all(self, request: Request) -> Response:
        from apps.platform.services.notification_feed import hide_all_platform_notifications

        count = hide_all_platform_notifications(request.user)
        return Response({"success": True, "message": f"{count} notification(s) removed from your inbox."})


class APIKeyViewSet(viewsets.ModelViewSet):
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["tenant", "is_active"]


class PlatformNewsViewSet(viewsets.ModelViewSet):
    queryset = PlatformNews.objects.all()
    serializer_class = PlatformNewsSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["is_published", "target"]

    def get_permissions(self):
        if self.action == "list" and self.request.query_params.get("public"):
            return [AllowAny()]
        return [IsSuperAdmin()]


class PlanAdvertisementViewSet(viewsets.ModelViewSet):
    """Super-admin plan upgrade advertisements for school notification feeds."""

    queryset = PlanAdvertisement.objects.select_related("created_by").all()
    serializer_class = PlanAdvertisementSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["status", "target_plan_slug", "suggested_plan_slug"]
    search_fields = ["title", "headline", "message"]
    ordering_fields = ["updated_at", "broadcast_at", "status", "target_plan_slug"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def plan_options(self, request: Request) -> Response:
        from apps.subscriptions.models import Plan

        plans = list(Plan.objects.filter(is_active=True).order_by("sort_order", "name"))
        payload = []
        for plan in plans:
            upgrades = get_upgrade_options(plan.slug)
            payload.append({
                "slug": plan.slug,
                "name": plan.name,
                "upgrade_options": [
                    {"slug": slug, "name": get_plan_label(slug)} for slug in upgrades
                ],
                "can_advertise": bool(upgrades),
            })
        return Response({"success": True, "data": payload})

    @action(detail=False, methods=["get"])
    def defaults(self, request: Request) -> Response:
        target = request.query_params.get("target_plan_slug", PLAN_ORDER[0])
        suggested = request.query_params.get("suggested_plan_slug")
        return Response({
            "success": True,
            "data": build_default_advertisement_payload(target, suggested),
        })

    @action(detail=True, methods=["post"])
    def broadcast(self, request: Request, pk: str = None) -> Response:
        ad = self.get_object()
        result = broadcast_plan_advertisement(ad, actor=request.user)
        ad.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Advertisement broadcast to {result['schools_notified']} school admin(s).",
            "data": {
                **PlanAdvertisementSerializer(ad).data,
                "broadcast_result": result,
            },
        })

    @action(detail=True, methods=["post"])
    def pause(self, request: Request, pk: str = None) -> Response:
        ad = self.get_object()
        ad.status = "paused"
        ad.save(update_fields=["status", "updated_at"])
        return Response({
            "success": True,
            "message": "Advertisement paused.",
            "data": PlanAdvertisementSerializer(ad).data,
        })

    @action(detail=True, methods=["post"])
    def end(self, request: Request, pk: str = None) -> Response:
        ad = self.get_object()
        ad.status = "ended"
        ad.ends_at = timezone.now()
        ad.save(update_fields=["status", "ends_at", "updated_at"])
        return Response({
            "success": True,
            "message": "Advertisement ended.",
            "data": PlanAdvertisementSerializer(ad).data,
        })


class PlatformBroadcastViewSet(viewsets.ModelViewSet):
    queryset = PlatformBroadcast.objects.all()
    serializer_class = PlatformBroadcastSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["is_active", "severity", "status", "audience"]
    search_fields = ["title", "message"]
    ordering_fields = ["starts_at", "created_at", "status"]

    def perform_create(self, serializer):
        from django.utils import timezone

        broadcast = serializer.save()
        if broadcast.status == "sent" and not broadcast.sent_at:
            broadcast.sent_at = timezone.now()
            broadcast.save(update_fields=["sent_at", "updated_at"])

    def perform_update(self, serializer):
        from django.utils import timezone

        previous = self.get_object()
        broadcast = serializer.save()
        if broadcast.status == "sent" and not broadcast.sent_at:
            broadcast.sent_at = timezone.now()
            broadcast.save(update_fields=["sent_at", "updated_at"])
        elif previous.status != "sent" and broadcast.status == "sent":
            broadcast.sent_at = timezone.now()
            broadcast.save(update_fields=["sent_at", "updated_at"])


class SystemHealthLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemHealthLog.objects.all()
    serializer_class = SystemHealthLogSerializer
    permission_classes = [IsSuperAdmin]


class SchoolsManagementView(APIView):
    """Super admin school management overview."""

    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        tenants = Tenant.objects.all().order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            tenants = tenants.filter(status=status_filter)
        return Response({
            "success": True,
            "count": tenants.count(),
            "results": TenantSerializer(tenants[:50], many=True).data,
        })


class HealthCheckView(APIView):
    """Public system health endpoint."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        start = time.monotonic()
        db_ok = True
        redis_ok = True

        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        try:
            cache.set("health_check", "ok", 10)
            redis_ok = cache.get("health_check") == "ok"
        except Exception:
            redis_ok = False

        elapsed_ms = int((time.monotonic() - start) * 1000)
        overall = "healthy" if db_ok and redis_ok else "degraded" if db_ok or redis_ok else "down"

        log = SystemHealthLog.objects.create(
            status=overall,
            database_ok=db_ok,
            redis_ok=redis_ok,
            celery_ok=True,
            response_time_ms=elapsed_ms,
            details={"maintenance_mode": settings.MAINTENANCE_MODE},
        )

        return Response({
            "success": True,
            "status": overall,
            "database": db_ok,
            "redis": redis_ok,
            "maintenance_mode": settings.MAINTENANCE_MODE,
            "response_time_ms": elapsed_ms,
            "checked_at": timezone.now().isoformat(),
            "log_id": str(log.id),
        }, status=status.HTTP_200_OK if overall != "down" else status.HTTP_503_SERVICE_UNAVAILABLE)


PLATFORM_SETTINGS_DEFAULTS = {
    "platform_name": "Apex Hub",
    "platform_tagline": "The Easy Way",
    "support_email": "support@apexhub.io",
    "default_plan": "premium",
    "max_upload_size": 10,
    "maintenance_mode": False,
    "default_timezone": "Africa/Kampala",
    "default_country": "Uganda",
}


class PublicPlatformSettingsView(APIView):
    """Public platform settings for registration onboarding."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = dict(PLATFORM_SETTINGS_DEFAULTS)
        for setting in GlobalSetting.objects.filter(key="platform_config"):
            data.update(setting.value)
        return Response({
            "success": True,
            "data": {
                "platform_name": data.get("platform_name"),
                "support_email": data.get("support_email"),
                "default_country": data.get("default_country"),
            },
        })


class PlatformSettingsView(APIView):
    """Consolidated platform settings for super-admin UI."""

    permission_classes = [IsSuperAdmin]

    def _load_settings(self) -> dict:
        data = dict(PLATFORM_SETTINGS_DEFAULTS)
        for setting in GlobalSetting.objects.filter(
            key__in=["platform_config", "maintenance_mode"],
        ):
            if setting.key == "maintenance_mode":
                data["maintenance_mode"] = bool(setting.value.get("enabled", False))
            elif setting.key == "platform_config":
                data.update(setting.value)
        data["maintenance_mode"] = data.get("maintenance_mode", settings.MAINTENANCE_MODE)
        return data

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": self._load_settings()})

    def patch(self, request: Request) -> Response:
        ser = PlatformSettingsSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        current = self._load_settings()
        current.update(payload)
        GlobalSetting.objects.update_or_create(
            key="platform_config",
            defaults={"value": {
                k: current[k] for k in PLATFORM_SETTINGS_DEFAULTS if k != "maintenance_mode"
            }},
        )
        if "maintenance_mode" in payload:
            from apps.platform.services.maintenance import set_maintenance_mode

            set_maintenance_mode(bool(payload["maintenance_mode"]))
        return Response({"success": True, "data": self._load_settings()})


class MaintenanceModeView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"maintenance_mode": settings.MAINTENANCE_MODE})

    def post(self, request: Request) -> Response:
        from apps.platform.services.maintenance import set_maintenance_mode

        enabled = bool(request.data.get("enabled", False))
        set_maintenance_mode(enabled)
        return Response({"success": True, "maintenance_mode": enabled})