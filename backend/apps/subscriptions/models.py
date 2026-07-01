"""Subscription and billing models."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import models
from django.utils import timezone

from apps.core.constants import SubscriptionStatus
from apps.core.models import PlatformModel


class FeatureCategory(PlatformModel):
    """Groups subscription features for admin plan configuration."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_feature_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Feature categories"

    def __str__(self) -> str:
        return self.name


class FeatureFlag(PlatformModel):
    """Individual assignable platform feature (catalog record)."""

    category = models.ForeignKey(
        FeatureCategory, on_delete=models.PROTECT, related_name="features",
    )
    feature_key = models.SlugField(max_length=80, unique=True, db_index=True)
    feature_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    nav_key = models.CharField(max_length=50, blank=True, help_text="Sidebar grouping key")
    route_path = models.CharField(max_length=120, blank=True, help_text="Frontend route path")
    icon = models.CharField(max_length=50, blank=True, default="FiGrid")
    show_in_nav = models.BooleanField(default=False)
    show_on_dashboard = models.BooleanField(default=False)
    widget_key = models.CharField(max_length=50, blank=True)
    dashboard_label = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_feature_flag"
        ordering = ["category__sort_order", "sort_order", "feature_name"]

    def __str__(self) -> str:
        return self.feature_name


class Plan(PlatformModel):
    """Subscription plan with limits and feature assignments."""

    class Meta:
        db_table = "subscriptions_plan"
        ordering = ["sort_order", "price_monthly"]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    max_students = models.PositiveIntegerField(default=100)
    max_staff = models.PositiveIntegerField(default=20)
    max_parents = models.PositiveIntegerField(default=500)
    max_branches = models.PositiveIntegerField(default=1)
    max_storage_mb = models.PositiveIntegerField(default=1024)
    max_sms_monthly = models.PositiveIntegerField(default=0)
    max_emails_monthly = models.PositiveIntegerField(default=500)
    trial_days = models.PositiveIntegerField(default=14)
    grace_period_days = models.PositiveIntegerField(default=7)

    features = models.ManyToManyField(
        FeatureFlag, through="PlanFeature", blank=True, related_name="plans",
    )
    feature_flags = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.name

    def sync_feature_flags(self) -> dict[str, bool]:
        from apps.subscriptions.services import build_plan_feature_flags, invalidate_plan_cache

        self.feature_flags = build_plan_feature_flags(self)
        invalidate_plan_cache(str(self.id))
        return self.feature_flags


class PlanFeature(models.Model):
    """Many-to-many link between plans and features."""

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_features")
    feature = models.ForeignKey(FeatureFlag, on_delete=models.CASCADE, related_name="plan_features")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscriptions_plan_feature"
        unique_together = [("plan", "feature")]

    def __str__(self) -> str:
        return f"{self.plan.name} → {self.feature.feature_key}"


class Subscription(models.Model):
    """Tenant subscription instance."""

    id = models.UUIDField(primary_key=True, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")

    status = models.CharField(max_length=20, choices=SubscriptionStatus.CHOICES, default=SubscriptionStatus.TRIAL)
    billing_cycle = models.CharField(max_length=20, choices=[("monthly", "Monthly"), ("yearly", "Yearly")], default="monthly")

    started_at = models.DateTimeField(default=timezone.now)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["status", "current_period_end"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.name} - {self.plan.name} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        import uuid
        from apps.subscriptions.services import invalidate_tenant_cache

        is_new = not self.id
        if not self.id:
            self.id = uuid.uuid4()
        if self.status == SubscriptionStatus.TRIAL and not self.trial_ends_at:
            self.trial_ends_at = timezone.now() + timedelta(days=self.plan.trial_days)
        super().save(*args, **kwargs)
        if not is_new or kwargs.get("update_fields"):
            invalidate_tenant_cache(str(self.tenant_id))

    @property
    def is_expired(self) -> bool:
        now = timezone.now()
        if self.status == SubscriptionStatus.TRIAL and self.trial_ends_at:
            return now > self.trial_ends_at
        if self.current_period_end:
            return now > self.current_period_end
        return self.status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED)

    @property
    def in_grace_period(self) -> bool:
        if self.grace_period_ends_at:
            return timezone.now() <= self.grace_period_ends_at
        return False

    def activate(self, period_days: int = 30) -> None:
        now = timezone.now()
        self.status = SubscriptionStatus.ACTIVE
        self.current_period_start = now
        self.current_period_end = now + timedelta(days=period_days)
        grace_days = self.plan.grace_period_days if self.plan else 7
        self.grace_period_ends_at = self.current_period_end + timedelta(days=grace_days)
        self.save()

    def suspend(self) -> None:
        self.status = SubscriptionStatus.SUSPENDED
        self.save(update_fields=["status", "updated_at"])


class PaymentProvider(PlatformModel):
    """Payment gateway configuration."""

    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=30, unique=True)
    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.name


class PaymentTransaction(PlatformModel):
    """Payment transaction record."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name="payments")
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT, related_name="transactions")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"), ("completed", "Completed"),
        ("failed", "Failed"), ("refunded", "Refunded"),
    ], default="pending")
    reference = models.CharField(max_length=255, unique=True, db_index=True)
    external_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status"])]