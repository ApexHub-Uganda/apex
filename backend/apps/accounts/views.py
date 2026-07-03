"""Account views."""
from __future__ import annotations

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import LoginHistory, User, UserDevice
from apps.accounts.permissions import CanManageUsers, CanViewOwnProfile
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    LoginHistorySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserCreateSerializer,
    UserDeviceSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.core.constants import UserRole
from apps.core.mixins import get_client_ip
from apps.core.permissions import TenantActivePermission


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login must ignore any stale Bearer token sent by the client."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]
    authentication_classes = ()


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({"success": True, "message": "Logged out successfully."})


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request: Request) -> Response:
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({
            "success": True,
            "message": "If the email exists, a reset link has been sent.",
        })


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"success": True, "message": "Password reset successfully."})


class MeView(generics.RetrieveUpdateAPIView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), TenantActivePermission()]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self) -> User:
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save()
        return Response({"success": True, "message": "Password changed successfully."})


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageUsers, TenantActivePermission]
    filterset_fields = ["role", "is_active", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering_fields = ["last_name", "created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.SUPER_ADMIN:
            tenant_id = self.request.query_params.get("tenant_id")
            qs = User.objects.all()
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            return qs
        return User.objects.filter(tenant=user.tenant)

    @action(detail=True, methods=["post"])
    def verify_email(self, request: Request, pk: str = None) -> Response:
        user = self.get_object()
        user.verify_email()
        return Response({"success": True, "message": "Email verified."})

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str = None) -> Response:
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return Response({"success": True, "message": "User deactivated."})


class LoginHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.SUPER_ADMIN:
            return LoginHistory.objects.all()
        if user.role == UserRole.SCHOOL_ADMIN:
            return LoginHistory.objects.filter(user__tenant=user.tenant)
        return LoginHistory.objects.filter(user=user)


class UserDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationFeedView(APIView):
    """Role-aware navbar notification feed for all authenticated users."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.communication.services import (
            get_navbar_user_notifications,
            get_unread_user_notifications,
        )
        from apps.core.constants import TenantStatus, UserRole
        from apps.platform.services.notification_feed import get_platform_notification_summary

        user = request.user

        if user.role == UserRole.SUPER_ADMIN:
            data = get_platform_notification_summary(user)
            return Response({
                "success": True,
                "data": {
                    "unread_count": data["unread_count"],
                    "items": data["recent"],
                    "feed_type": "platform",
                    "view_all_url": "/super-admin/notifications",
                },
            })

        from apps.communication.services import get_dismissed_feed_item_ids

        dismissed_ids = get_dismissed_feed_item_ids(user)
        items = [
            item for item in get_navbar_user_notifications(user, limit=5)
            if item.get("id") not in dismissed_ids
        ]
        unread_count = get_unread_user_notifications(user)

        tenant = getattr(user, "tenant", None)

        if tenant:
            from apps.platform.services.plan_advertisements import get_active_plan_advertisements_for_tenant

            ad_items = get_active_plan_advertisements_for_tenant(tenant)
            if ad_items:
                existing_ids = {i.get("id") for i in items}
                pinned = [
                    ad for ad in ad_items
                    if ad.get("id") not in existing_ids and ad.get("id") not in dismissed_ids
                ]
                items = [*pinned, *items]

        if tenant and (tenant.status == TenantStatus.PENDING or not tenant.is_verified):
            pending_id = f"pending-{tenant.id}"
            if pending_id not in dismissed_ids:
                pending_item = {
                    "id": pending_id,
                    "title": "Account pending approval",
                    "message": "Your school account is awaiting super admin approval before dashboard access is granted.",
                    "type": "warning",
                    "is_read": False,
                    "priority": "high",
                    "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
                    "action_url": "/school-admin",
                    "metadata": {"synthetic": True},
                }
                if not any(i.get("title") == pending_item["title"] for i in items):
                    items = [pending_item, *items]
                if not any(not i.get("is_read") for i in items):
                    unread_count = max(unread_count, 1)

        return Response({
            "success": True,
            "data": {
                "unread_count": unread_count,
                "items": items,
                "feed_type": "user",
                "view_all_url": "/school-admin/notifications",
            },
        })

    def post(self, request: Request) -> Response:
        from apps.communication.services import (
            delete_all_user_notifications,
            delete_user_feed_item,
            dismiss_feed_item,
            dismiss_feed_items,
            get_dismissed_feed_item_ids,
            is_synthetic_feed_item,
            mark_all_user_notifications_read,
        )
        from apps.core.constants import TenantStatus, UserRole
        from apps.platform.services.notification_feed import (
            hide_all_platform_notifications,
            hide_platform_notification_by_id,
            mark_all_platform_notifications_read,
        )
        from apps.platform.services.plan_advertisements import get_active_plan_advertisements_for_tenant

        user = request.user
        action = request.data.get("action", "mark_all_read")
        item_id = request.data.get("item_id")

        if action == "mark_all_read":
            if user.role == UserRole.SUPER_ADMIN:
                count = mark_all_platform_notifications_read(user)
            else:
                count = mark_all_user_notifications_read(user)
            return Response({"success": True, "message": f"{count} notifications marked as read."})

        if action == "delete_one":
            if not item_id:
                return Response({"success": False, "error": {"message": "item_id is required."}}, status=400)
            if user.role == UserRole.SUPER_ADMIN:
                deleted = hide_platform_notification_by_id(user, item_id)
            else:
                deleted = delete_user_feed_item(user, item_id)
            if not deleted:
                return Response({"success": False, "error": {"message": "Notification not found."}}, status=404)
            return Response({"success": True, "message": "Notification deleted."})

        if action == "delete_all":
            if user.role == UserRole.SUPER_ADMIN:
                count = hide_all_platform_notifications(user)
            else:
                count = delete_all_user_notifications(user)
                synthetic_ids = []
                tenant = getattr(user, "tenant", None)
                if tenant:
                    synthetic_ids.extend(
                        ad["id"] for ad in get_active_plan_advertisements_for_tenant(tenant)
                    )
                    if tenant.status == TenantStatus.PENDING or not tenant.is_verified:
                        synthetic_ids.append(f"pending-{tenant.id}")
                dismissed = dismiss_feed_items(user, synthetic_ids)
                count += dismissed
            return Response({"success": True, "message": f"{count} notification(s) deleted."})

        return Response({"success": False, "error": {"message": "Unsupported action."}}, status=400)