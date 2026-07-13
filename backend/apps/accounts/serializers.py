"""Account serializers."""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from apps.accounts.avatar_serializers import AvatarFieldsMixin
from apps.accounts.models import LoginHistory, User, UserDevice, UserSession
from apps.core.constants import UserRole, normalize_role
from apps.core.serializer_fields import DeliverableEmailField
from apps.core.mixins import get_client_ip


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login with tenant and role claims."""

    @classmethod
    def get_token(cls, user: User) -> Any:
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        if user.tenant_id:
            token["tenant_id"] = str(user.tenant_id)
            token["tenant_name"] = user.tenant.name if user.tenant else ""
            token["tenant_is_suspended"] = bool(user.tenant and user.tenant.is_suspended)
            token["tenant_status"] = user.tenant.status if user.tenant else ""
            sub = user.tenant.active_subscription if user.tenant else None
            if sub and sub.plan:
                token["tenant_plan_slug"] = sub.plan.slug
        token["must_change_password"] = bool(getattr(user, "must_change_password", False))
        return token

    def validate(self, attrs: dict) -> dict:
        request = self.context.get("request")
        email = attrs.get("email", "")

        try:
            data = super().validate(attrs)
            success = True
            failure_reason = ""
        except Exception as exc:
            LoginHistory.objects.create(
                email=email,
                success=False,
                ip_address=get_client_ip(request) if request else None,
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
                failure_reason=str(exc.detail) if hasattr(exc, "detail") else "Invalid credentials",
            )
            raise

        user = self.user

        from django.conf import settings as django_settings

        if getattr(django_settings, "MAINTENANCE_MODE", False) and user.role != UserRole.SUPER_ADMIN:
            raise serializers.ValidationError(
                "Apex Hub is currently under maintenance. Please try again later.",
                code="maintenance_mode",
            )

        user.last_login_at = timezone.now()
        if request:
            user.last_login_ip = get_client_ip(request)
        user.save(update_fields=["last_login_at", "last_login_ip", "updated_at"])

        LoginHistory.objects.create(
            user=user,
            email=user.email,
            success=success,
            ip_address=user.last_login_ip,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        )

        data["user"] = UserSerializer(user).data
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Block token refresh for non–super-admins during maintenance."""

    def validate(self, attrs: dict) -> dict:
        from django.conf import settings as django_settings

        data = super().validate(attrs)
        if getattr(django_settings, "MAINTENANCE_MODE", False):
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken(attrs["refresh"])
            user = User.objects.filter(pk=refresh.get("user_id")).first()
            if not user or user.role != UserRole.SUPER_ADMIN:
                raise serializers.ValidationError(
                    "Apex Hub is currently under maintenance. Please try again later.",
                    code="maintenance_mode",
                )
        return data


class UserSerializer(AvatarFieldsMixin, serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, allow_null=True)
    tenant_status = serializers.CharField(source="tenant.status", read_only=True, allow_null=True)
    tenant_is_verified = serializers.BooleanField(source="tenant.is_verified", read_only=True, allow_null=True)
    tenant_is_suspended = serializers.BooleanField(source="tenant.is_suspended", read_only=True, allow_null=True)
    tenant_registration_type = serializers.CharField(
        source="tenant.registration_type", read_only=True, allow_null=True,
    )
    tenant_plan_slug = serializers.SerializerMethodField()
    effective_role = serializers.SerializerMethodField()
    is_school_admin = serializers.SerializerMethodField()
    is_school_portal_user = serializers.SerializerMethodField()
    module_permissions = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "phone",
            "avatar", "avatar_url", "has_avatar", "role", "effective_role", "tenant", "tenant_name", "tenant_status",
            "tenant_plan_slug", "is_school_admin", "is_school_portal_user",
            "module_permissions", "permissions",
            "tenant_is_verified", "tenant_is_suspended", "tenant_registration_type", "is_active",
            "is_email_verified", "is_2fa_enabled", "must_change_password", "last_login_at", "created_at",
        ]
        read_only_fields = [
            "id", "is_email_verified", "is_2fa_enabled", "last_login_at", "created_at",
        ]

    def get_tenant_plan_slug(self, obj: User) -> str | None:
        if not obj.tenant_id:
            return None
        tenant = obj.tenant
        if tenant is None:
            return None
        sub = tenant.active_subscription
        return sub.plan.slug if sub and sub.plan else None

    def get_effective_role(self, obj: User) -> str:
        return normalize_role(obj.role)

    def get_is_school_admin(self, obj: User) -> bool:
        return obj.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)

    def get_is_school_portal_user(self, obj: User) -> bool:
        return obj.role in UserRole.SCHOOL_PORTAL_ROLES or obj.role == UserRole.SUPER_ADMIN

    def _resolve_module_permissions(self, obj: User) -> dict[str, dict[str, bool]]:
        if not obj.tenant_id:
            return {}
        tenant = obj.tenant
        if tenant is None:
            return {}
        from apps.tenants.role_permissions import get_user_module_permissions

        return get_user_module_permissions(tenant, obj)

    def get_module_permissions(self, obj: User) -> dict[str, dict[str, bool]]:
        return self._resolve_module_permissions(obj)

    def get_permissions(self, obj: User) -> list[str]:
        from apps.tenants.role_permissions import (
            get_user_feature_permissions,
            permissions_to_strings,
        )

        if not obj.tenant_id:
            return permissions_to_strings(self._resolve_module_permissions(obj))
        tenant = obj.tenant
        if tenant is None:
            return permissions_to_strings(self._resolve_module_permissions(obj))
        return permissions_to_strings(
            self._resolve_module_permissions(obj),
            get_user_feature_permissions(tenant, obj),
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = DeliverableEmailField()

    class Meta:
        model = User
        fields = [
            "email", "password", "first_name", "last_name", "phone",
            "role", "tenant", "is_active",
        ]

    def validate_role(self, value: str) -> str:
        request = self.context.get("request")
        if request and request.user.role == UserRole.SCHOOL_ADMIN:
            if value == UserRole.SUPER_ADMIN:
                raise serializers.ValidationError("Cannot assign super_admin role.")
            if value not in UserRole.SCHOOL_PORTAL_ROLES:
                raise serializers.ValidationError("Invalid school portal role.")
        return value

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        request = self.context.get("request")
        if request and request.user.tenant_id and "tenant" not in validated_data:
            validated_data["tenant"] = request.user.tenant
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar", "role", "is_active"]

    def validate_role(self, value: str) -> str:
        request = self.context.get("request")
        if request and request.user.role == UserRole.SCHOOL_ADMIN:
            if value == UserRole.SUPER_ADMIN:
                raise serializers.ValidationError("Cannot assign super_admin role.")
            if value not in UserRole.SCHOOL_PORTAL_ROLES:
                raise serializers.ValidationError("Invalid school portal role.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        new_password = attrs.get("new_password", "")
        confirm_password = attrs.get("confirm_password") or new_password
        if confirm_password != new_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        if getattr(user, "must_change_password", False):
            return attrs

        old_password = attrs.get("old_password") or ""
        if not old_password:
            raise serializers.ValidationError({"old_password": "Current password is required."})
        if not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Current password is incorrect."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = DeliverableEmailField()

    def save(self) -> dict:
        from apps.accounts.password_reset import PasswordResetError, send_password_reset_otp

        try:
            return send_password_reset_otp(email=self.validated_data["email"])
        except PasswordResetError as exc:
            raise serializers.ValidationError({"email": exc.message}) from exc


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = DeliverableEmailField()
    otp = serializers.RegexField(
        regex=r"^\d{6}$",
        min_length=6,
        max_length=6,
        error_messages={"invalid": "Enter the 6-digit verification code from your email."},
    )
    new_password = serializers.CharField(min_length=8, write_only=True)

    def save(self) -> User:
        from apps.accounts.password_reset import PasswordResetError, confirm_password_reset

        try:
            return confirm_password_reset(
                email=self.validated_data["email"],
                otp=self.validated_data["otp"],
                new_password=self.validated_data["new_password"],
            )
        except PasswordResetError as exc:
            field = "otp" if exc.code.startswith("otp") else "email"
            raise serializers.ValidationError({field: exc.message}) from exc


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            "id", "device_name", "device_type", "ip_address",
            "is_active", "last_activity", "created_at", "expires_at",
        ]


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            "id", "device_id", "device_name", "platform",
            "is_trusted", "last_seen", "created_at",
        ]
        read_only_fields = ["id", "last_seen", "created_at"]


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = [
            "id", "email", "success", "ip_address",
            "failure_reason", "created_at",
        ]