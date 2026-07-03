from django.contrib import admin

from apps.subscriptions.models import (
    FeatureCategory,
    FeatureFlag,
    PaymentProvider,
    PaymentTransaction,
    Plan,
    PlanFeature,
    Subscription,
)


@admin.register(FeatureCategory)
class FeatureCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "sort_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["feature_name", "feature_key", "category", "nav_key", "is_active"]
    list_filter = ["category", "is_active", "show_in_nav"]
    search_fields = ["feature_key", "feature_name"]
    prepopulated_fields = {"feature_key": ("feature_name",)}


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ["plan", "feature", "created_at"]
    list_filter = ["plan"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "price_monthly", "max_students", "is_active", "sort_order"]
    list_filter = ["is_active", "is_public"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "plan", "status", "current_period_end", "auto_renew"]
    list_filter = ["status", "billing_cycle"]


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "method_type", "is_active", "is_sandbox"]
    list_filter = ["method_type", "is_active"]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["reference", "tenant", "amount", "payment_method", "status", "created_at"]
    list_filter = ["status", "payment_method"]