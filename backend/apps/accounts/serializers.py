"""Account serializers."""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from apps.accounts.models import LoginHistory, User, UserDevice, UserSession
from apps.core.constants import UserRole
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


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, allow_null=True)
    tenant_status = serializers.CharField(source="tenant.status", read_only=True, allow_null=True)
    tenant_is_verified = serializers.BooleanField(source="tenant.is_verified", read_only=True, allow_null=True)
    tenant_is_suspended = serializers.BooleanField(source="tenant.is_suspended", read_only=True, allow_null=True)
    tenant_registration_type = serializers.CharField(
        source="tenant.registration_type", read_only=True, allow_null=True,
    )
    tenant_plan_slug = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "phone",
            "avatar", "role", "tenant", "tenant_name", "tenant_status",
            "tenant_plan_slug",
            "tenant_is_verified", "tenant_is_suspended", "tenant_registration_type", "is_active",
            "is_email_verified", "is_2fa_enabled", "last_login_at", "created_at",
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


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

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
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self) -> None:
        email = self.validated_data["email"]
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return
        user.password_reset_token = secrets.token_urlsafe(32)
        user.password_reset_expires = timezone.now() + timedelta(hours=24)
        user.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])
        # Email would be sent via communication app in production


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs: dict) -> dict:
        try:
            user = User.objects.get(
                password_reset_token=attrs["token"],
                password_reset_expires__gt=timezone.now(),
            )
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid or expired reset token."})
        attrs["user"] = user
        return attrs

    def save(self) -> User:
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.password_reset_token = ""
        user.password_reset_expires = None
        user.save()
        return user


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