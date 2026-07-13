"""Tenant serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.serializer_fields import DeliverableEmailField
from apps.staff.models import Staff
from apps.students.models import Student
from apps.tenants.models import Tenant
from apps.tenants.school_validation import (
    validate_school_code,
    validate_school_contact_email,
    validate_school_name,
)


class TenantBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "logo", "favicon", "banner", "login_bg",
            "primary_color", "secondary_color", "accent_color", "tagline",
        ]


class TenantSerializer(serializers.ModelSerializer):
    enabled_features = serializers.SerializerMethodField()
    enabled_feature_keys = serializers.SerializerMethodField()
    feature_flags = serializers.SerializerMethodField()
    navigation_menu = serializers.SerializerMethodField()
    module_menu = serializers.SerializerMethodField()
    dashboard_widgets = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    features_revision = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "code", "email", "phone", "address",
            "city", "country", "timezone", "logo", "favicon", "banner",
            "login_bg", "primary_color", "secondary_color", "accent_color",
            "tagline", "status", "is_verified", "is_suspended", "website",
            "registration_number", "registration_type", "payment_attempted",
            "enabled_features", "enabled_feature_keys",
            "feature_flags", "navigation_menu", "module_menu", "dashboard_widgets",
            "subscription", "features_revision", "created_at",
        ]
        read_only_fields = ["id", "slug", "status", "is_verified", "is_suspended", "created_at"]

    def get_enabled_features(self, obj: Tenant) -> list[str]:
        return obj.get_enabled_features()

    def get_enabled_feature_keys(self, obj: Tenant) -> list[str]:
        from apps.subscriptions.services import get_enabled_feature_keys
        return get_enabled_feature_keys(obj)

    def get_feature_flags(self, obj: Tenant) -> dict[str, bool]:
        return obj.get_feature_flags()

    def get_navigation_menu(self, obj: Tenant) -> list[dict]:
        return obj.get_navigation_menu()

    def get_module_menu(self, obj: Tenant) -> list[dict]:
        from apps.subscriptions.services import get_tenant_module_menu
        return get_tenant_module_menu(obj)

    def get_features_revision(self, obj: Tenant) -> str:
        from apps.subscriptions.services import get_enabled_feature_keys, get_tenant_module_menu

        sub = obj.active_subscription
        if not sub or not sub.plan:
            return "none"
        keys = get_enabled_feature_keys(obj)
        modules = get_tenant_module_menu(obj)
        return f"{sub.plan_id}:{sub.updated_at.isoformat()}:{len(keys)}:{len(modules)}"

    def get_dashboard_widgets(self, obj: Tenant) -> list[dict]:
        return obj.get_dashboard_widgets()

    def get_subscription(self, obj: Tenant) -> dict | None:
        from apps.subscriptions.services import get_subscription_summary
        return get_subscription_summary(obj)


class TenantRegistrationSerializer(serializers.ModelSerializer):
    email = DeliverableEmailField(required=False, allow_blank=True)
    admin_email = DeliverableEmailField(write_only=True)
    admin_password = serializers.CharField(write_only=True, min_length=8)
    admin_first_name = serializers.CharField(write_only=True, max_length=100)
    admin_last_name = serializers.CharField(write_only=True, max_length=100)
    code = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = Tenant
        fields = [
            "name", "code", "email", "phone", "address", "city", "country",
            "registration_number", "website",
            "admin_email", "admin_password", "admin_first_name", "admin_last_name",
        ]

    def validate_name(self, value: str) -> str:
        return validate_school_name(value)

    def validate_email(self, value: str) -> str:
        if not value:
            return value
        return validate_school_contact_email(value)

    def validate_admin_email(self, value: str) -> str:
        return validate_school_contact_email(value)

    def validate_code(self, value: str) -> str:
        if not value:
            return value
        code = validate_school_code(value)
        if Tenant.objects.filter(code__iexact=code).exists():
            raise serializers.ValidationError("School code already exists.")
        return code

    def validate(self, attrs: dict) -> dict:
        from apps.accounts.models import User

        if not attrs.get("email"):
            attrs["email"] = attrs["admin_email"]

        admin_email = str(attrs.get("admin_email", "")).strip().lower()
        school_email = str(attrs.get("email", "")).strip().lower()
        if admin_email and User.objects.filter(email__iexact=admin_email).exists():
            raise serializers.ValidationError({
                "admin_email": "An account with this email already exists. Sign in or use a different email.",
            })
        if school_email and school_email != admin_email and User.objects.filter(email__iexact=school_email).exists():
            raise serializers.ValidationError({
                "email": "An account with this school email already exists.",
            })
        return attrs

    def create(self, validated_data: dict) -> Tenant:
        from apps.accounts.models import User
        from apps.core.constants import RegistrationType, UserRole
        from apps.platform.services.notifications import create_registration_notification
        from apps.tenants.utils import generate_school_code

        admin_data = {
            "email": validated_data.pop("admin_email"),
            "password": validated_data.pop("admin_password"),
            "first_name": validated_data.pop("admin_first_name"),
            "last_name": validated_data.pop("admin_last_name"),
        }

        code = validated_data.pop("code", "") or generate_school_code(validated_data["name"])
        validated_data["code"] = code.upper()
        validated_data.setdefault("registration_type", RegistrationType.PENDING)

        tenant = Tenant.objects.create(**validated_data)

        User.objects.create_user(
            email=admin_data["email"],
            password=admin_data["password"],
            first_name=admin_data["first_name"],
            last_name=admin_data["last_name"],
            role=UserRole.SCHOOL_ADMIN,
            tenant=tenant,
            is_email_verified=False,
        )

        create_registration_notification(
            tenant,
            registration_type=RegistrationType.PENDING,
        )

        from apps.subscriptions.models import Plan, Subscription
        trial_plan = Plan.objects.filter(slug="free_trial", is_active=True).first()
        if trial_plan:
            Subscription.objects.create(tenant=tenant, plan=trial_plan, status="trial")

        return tenant


class TenantMinimalListSerializer(serializers.ModelSerializer):
    """Minimal school row for super-admin directory."""

    class Meta:
        model = Tenant
        fields = ["id", "name", "country"]


class TenantAdminListSerializer(serializers.ModelSerializer):
    """Enriched tenant row for super-admin school management."""

    plan = serializers.SerializerMethodField()
    plan_slug = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    staff_count = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    city_display = serializers.CharField(source="city", read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "code", "email", "phone", "city", "city_display", "country",
            "plan", "plan_slug", "status", "is_verified", "is_suspended", "registration_type",
            "students", "staff_count", "subscription_status", "created_at",
        ]

    def get_plan(self, obj: Tenant) -> str:
        sub = obj.active_subscription
        return sub.plan.name if sub and sub.plan else "—"

    def get_plan_slug(self, obj: Tenant) -> str | None:
        sub = obj.active_subscription
        return sub.plan.slug if sub and sub.plan else None

    def get_students(self, obj: Tenant) -> int:
        return Student.objects.filter(tenant=obj, is_deleted=False).count()

    def get_staff_count(self, obj: Tenant) -> int:
        return Staff.objects.filter(tenant=obj, is_deleted=False).count()

    def get_subscription_status(self, obj: Tenant) -> str:
        sub = obj.active_subscription
        return sub.status if sub else "none"


class TenantAdminCreateSerializer(serializers.ModelSerializer):
    """Super-admin school creation with optional admin account."""

    email = DeliverableEmailField(required=False, allow_blank=True)
    admin_email = DeliverableEmailField(write_only=True, required=False, allow_blank=True)
    admin_password = serializers.CharField(write_only=True, required=False, min_length=8)
    admin_first_name = serializers.CharField(write_only=True, required=False, default="School")
    admin_last_name = serializers.CharField(write_only=True, required=False, default="Admin")
    plan_slug = serializers.SlugField(write_only=True, required=False)

    class Meta:
        model = Tenant
        fields = [
            "name", "code", "email", "phone", "address", "city", "country",
            "status", "admin_email", "admin_password", "admin_first_name",
            "admin_last_name", "plan_slug",
        ]

    def validate_name(self, value: str) -> str:
        return validate_school_name(value)

    def validate_email(self, value: str) -> str:
        if not value:
            return value
        return validate_school_contact_email(value)

    def validate_admin_email(self, value: str) -> str:
        if not value:
            return value
        return validate_school_contact_email(value)

    def validate_code(self, value: str) -> str:
        code = validate_school_code(value)
        if Tenant.objects.filter(code__iexact=code).exists():
            raise serializers.ValidationError("School code already exists.")
        return code

    def create(self, validated_data: dict) -> Tenant:
        from apps.accounts.models import User
        from apps.core.constants import UserRole
        from apps.subscriptions.models import Plan, Subscription

        admin_email = validated_data.pop("admin_email", None)
        admin_password = validated_data.pop("admin_password", None)
        admin_first_name = validated_data.pop("admin_first_name", "School")
        admin_last_name = validated_data.pop("admin_last_name", "Admin")
        plan_slug = validated_data.pop("plan_slug", "free_trial")
        validated_data.setdefault("is_verified", True)
        validated_data.setdefault("status", "active")

        tenant = Tenant.objects.create(**validated_data)
        if tenant.is_verified and not tenant.verified_at:
            tenant.verify()

        admin_user = None
        if admin_email and admin_password:
            admin_user = User.objects.create_user(
                email=admin_email,
                password=admin_password,
                first_name=admin_first_name,
                last_name=admin_last_name,
                role=UserRole.SCHOOL_ADMIN,
                tenant=tenant,
                is_email_verified=True,
            )

        plan = Plan.objects.filter(slug=plan_slug, is_active=True).first()
        if plan:
            from apps.tenants.services import assign_tenant_plan

            request = self.context.get("request")
            actor = request.user if request and request.user.is_authenticated else admin_user
            assign_tenant_plan(
                tenant,
                plan,
                subscription_status="active" if plan_slug != "free_trial" else "trial",
                period_days=30,
                actor=actor,
            )

        return tenant


class TenantAdminUpdateSerializer(serializers.ModelSerializer):
    email = DeliverableEmailField(required=False, allow_blank=True)

    class Meta:
        model = Tenant
        fields = [
            "name", "email", "phone", "address", "city", "country",
            "status", "is_verified", "website", "registration_number", "tagline",
        ]


class TenantSuspendSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class TenantChangePlanSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField()
    billing_cycle = serializers.ChoiceField(choices=["monthly", "yearly"], default="monthly")
    subscription_status = serializers.ChoiceField(
        choices=["trial", "active", "grace_period"],
        default="trial",
    )
    period_days = serializers.IntegerField(min_value=1, max_value=365, default=30, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_plan_slug(self, value: str) -> str:
        from apps.subscriptions.models import Plan

        if not Plan.objects.filter(slug=value, is_active=True).exists():
            raise serializers.ValidationError("Plan not found or inactive.")
        return value


class TenantPermanentDeleteSerializer(serializers.Serializer):
    confirmation_name = serializers.CharField(max_length=255)
    acknowledge_permanent = serializers.BooleanField()

    def validate_acknowledge_permanent(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge that this deletion is permanent and irreversible.",
            )
        return value


class ResetRolePermissionsSerializer(serializers.Serializer):
    role = serializers.CharField(required=False, allow_blank=True, default="")
    acknowledge_risk = serializers.BooleanField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_acknowledge_risk(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge that resetting permissions can expose risky operations.",
            )
        return value

    def validate_password(self, value: str) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value