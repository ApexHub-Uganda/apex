"""Subscription serializers."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.subscriptions.models import (
    FeatureCategory,
    FeatureFlag,
    PaymentProvider,
    PaymentTransaction,
    Plan,
    Subscription,
)
from apps.subscriptions.plan_tiers import (
    PlanInheritanceError,
    get_inherited_feature_keys,
    get_parent_tier_slug,
    get_plan_feature_breakdown,
    get_plan_tier_label,
    validate_plan_feature_inheritance,
)
from apps.subscriptions.services import assign_plan_features, invalidate_catalog_cache


class FeatureFlagSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = FeatureFlag
        fields = [
            "id", "feature_key", "feature_name", "description",
            "category", "category_name", "category_slug",
            "nav_key", "route_path", "icon",
            "show_in_nav", "show_on_dashboard", "widget_key", "dashboard_label",
            "sort_order", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_feature_key(self, value: str) -> str:
        qs = FeatureFlag.objects.filter(feature_key=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Feature key already exists.")
        return value


class FeatureCategorySerializer(serializers.ModelSerializer):
    features = FeatureFlagSerializer(many=True, read_only=True)

    class Meta:
        model = FeatureCategory
        fields = ["id", "slug", "name", "description", "sort_order", "is_active", "features", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        qs = FeatureCategory.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Category name already exists.")
        return value


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    enabled_feature_keys = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False,
    )
    enabled_features_detail = FeatureFlagSerializer(source="features", many=True, read_only=True)
    price = serializers.DecimalField(source="price_monthly", max_digits=10, decimal_places=2, read_only=True)
    billing_cycle = serializers.SerializerMethodField()
    subscriber_count = serializers.SerializerMethodField()
    inherits_from_slug = serializers.SerializerMethodField()
    inherits_from_label = serializers.SerializerMethodField()
    inherited_feature_keys = serializers.SerializerMethodField()
    exclusive_feature_keys = serializers.SerializerMethodField()
    feature_inheritance_summary = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "description", "price_monthly", "price_yearly",
            "price", "billing_cycle", "currency", "is_active", "is_public",
            "max_students", "max_staff", "max_parents", "max_branches",
            "max_storage_mb", "max_sms_monthly", "max_emails_monthly",
            "trial_days", "grace_period_days", "feature_flags",
            "enabled_feature_keys", "enabled_features_detail", "features",
            "inherits_from_slug", "inherits_from_label", "inherited_feature_keys",
            "exclusive_feature_keys", "feature_inheritance_summary",
            "subscriber_count", "sort_order", "created_at", "updated_at",
        ]

    def validate_price_monthly(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Monthly price cannot be negative.")
        return value

    def validate_price_yearly(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Yearly price cannot be negative.")
        return value

    def validate(self, attrs: dict) -> dict:
        limits = ["max_students", "max_staff", "max_parents", "max_branches",
                  "max_storage_mb", "max_sms_monthly", "max_emails_monthly",
                  "trial_days", "grace_period_days"]
        for field in limits:
            val = attrs.get(field, getattr(self.instance, field, None) if self.instance else None)
            if val is not None and val < 0:
                raise serializers.ValidationError({field: "Must be zero or greater."})
        return attrs

    def get_features(self, obj: Plan) -> list[str]:
        return list(
            obj.features.filter(is_active=True)
            .order_by("category__sort_order", "sort_order")
            .values_list("feature_name", flat=True)
        )

    def get_billing_cycle(self, obj: Plan) -> str:
        return "monthly"

    def get_subscriber_count(self, obj: Plan) -> int:
        return obj.subscriptions.filter(status__in=["trial", "active", "grace_period"]).count()

    def get_inherits_from_slug(self, obj: Plan) -> str | None:
        return get_parent_tier_slug(obj.slug)

    def get_inherits_from_label(self, obj: Plan) -> str | None:
        parent = get_parent_tier_slug(obj.slug)
        return get_plan_tier_label(parent) if parent else None

    def get_inherited_feature_keys(self, obj: Plan) -> list[str]:
        return sorted(get_inherited_feature_keys(obj.slug))

    def get_exclusive_feature_keys(self, obj: Plan) -> list[str]:
        inherited = get_inherited_feature_keys(obj.slug)
        exclusive = set(
            obj.features.filter(is_active=True).values_list("feature_key", flat=True),
        ) - inherited
        return sorted(exclusive)

    def get_feature_inheritance_summary(self, obj: Plan) -> str | None:
        return get_plan_feature_breakdown(obj).get("inherited_summary")

    def validate_enabled_feature_keys(self, value: list[str]) -> list[str]:
        slug = self.initial_data.get("slug") or getattr(self.instance, "slug", None)
        if slug and value is not None:
            try:
                validate_plan_feature_inheritance(slug, value)
            except PlanInheritanceError as exc:
                raise serializers.ValidationError(str(exc)) from exc
        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> Plan:
        keys = validated_data.pop("enabled_feature_keys", [])
        plan = Plan.objects.create(**validated_data)
        if keys is not None:
            assign_plan_features(plan, keys)
        return plan

    @transaction.atomic
    def update(self, instance: Plan, validated_data: dict) -> Plan:
        keys = validated_data.pop("enabled_feature_keys", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if keys is not None:
            assign_plan_features(instance, keys)
        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_slug = serializers.CharField(source="plan.slug", read_only=True)
    school = serializers.CharField(source="tenant.name", read_only=True)
    school_id = serializers.UUIDField(source="tenant.id", read_only=True)
    plan = serializers.CharField(source="plan.name", read_only=True)
    amount = serializers.SerializerMethodField()
    next_billing = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    in_grace_period = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "tenant", "school", "school_id", "plan", "plan_name", "plan_slug", "amount",
            "status", "billing_cycle", "next_billing", "started_at", "trial_ends_at",
            "current_period_start", "current_period_end", "grace_period_ends_at",
            "auto_renew", "is_expired", "in_grace_period", "created_at",
        ]
        read_only_fields = ["id", "started_at", "created_at"]

    def get_amount(self, obj: Subscription) -> float:
        if obj.billing_cycle == "yearly":
            return float(obj.plan.price_yearly / 12) if obj.plan else 0.0
        return float(obj.plan.price_monthly) if obj.plan else 0.0

    def get_next_billing(self, obj: Subscription) -> str | None:
        if obj.current_period_end:
            return obj.current_period_end.date().isoformat()
        if obj.trial_ends_at:
            return obj.trial_ends_at.date().isoformat()
        return None


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["tenant", "plan", "billing_cycle", "auto_renew"]


class PaymentProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProvider
        fields = ["id", "name", "slug", "method_type", "is_active", "is_sandbox"]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    school = serializers.CharField(source="tenant.name", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            "id", "tenant", "school", "subscription", "provider", "provider_name",
            "amount", "currency", "status", "reference", "payment_method", "payer_phone",
            "external_id", "metadata", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]