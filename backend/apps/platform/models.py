"""Platform-wide settings and configuration."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import PlatformModel


class GlobalSetting(PlatformModel):
    """Key-value platform settings."""

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class EmailSetting(PlatformModel):
    """Email gateway configuration."""

    provider = models.CharField(max_length=50, default="smtp")
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    from_email = models.EmailField(default="noreply@apexhub.io")
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Email setting"


class CallSetting(PlatformModel):
    """Voice / call gateway configuration."""

    provider = models.CharField(max_length=50, choices=[
        ("twilio", "Twilio"),
        ("africas_talking", "Africa's Talking"),
        ("nexmo", "Nexmo"),
        ("custom", "Custom"),
    ], default="twilio")
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    from_number = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Call setting"


class PlatformNotification(PlatformModel):
    """Super-admin notifications and actionable to-do items."""

    TYPE_CHOICES = [
        ("school_registration", "School Registration"),
        ("trial_request", "Trial Request"),
        ("payment_attempt", "Payment Attempt"),
        ("account_activation", "Account Activation"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("dismissed", "Dismissed"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="platform_notifications",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    action_taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="platform_notifications_actioned",
    )
    action_taken_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "notification_type"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["is_read", "status"]),
        ]


class PlatformNotificationReceipt(PlatformModel):
    """Per-user read state for super-admin platform notifications."""

    notification = models.ForeignKey(
        PlatformNotification, on_delete=models.CASCADE, related_name="receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="platform_notification_receipts",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("notification", "user")]
        indexes = [models.Index(fields=["user", "is_read"])]


class SMSSetting(PlatformModel):
    """SMS gateway configuration."""

    provider = models.CharField(max_length=50, choices=[
        ("africas_talking", "Africa's Talking"),
        ("twilio", "Twilio"),
        ("nexmo", "Nexmo"),
        ("custom", "Custom"),
    ], default="africas_talking")
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    sender_id = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "SMS setting"


class APIKey(PlatformModel):
    """Platform API keys for integrations."""

    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=10)
    key_hash = models.CharField(max_length=128)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="api_keys")
    scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API key"
        indexes = [models.Index(fields=["key_prefix", "is_active"])]


class PlatformNews(PlatformModel):
    """Platform news and updates."""

    title = models.CharField(max_length=255)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    target = models.CharField(max_length=20, choices=[
        ("all", "All Users"), ("schools", "School Admins"), ("public", "Public"),
    ], default="all")

    class Meta:
        ordering = ["-published_at"]
        verbose_name_plural = "Platform news"


class PlatformBroadcast(PlatformModel):
    """System-wide broadcast messages."""

    AUDIENCE_CHOICES = [
        ("all", "All Schools"),
        ("trial", "Trial Plans"),
        ("basic", "Basic Plans"),
        ("premium", "Premium Plans"),
        ("premium_plus", "Premium Plus Plans"),
        ("active", "Active Schools Only"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("sent", "Sent"),
        ("expired", "Expired"),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default="all")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    severity = models.CharField(max_length=10, choices=[
        ("info", "Info"), ("warning", "Warning"), ("critical", "Critical"),
    ], default="info")
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_at"]


class SystemHealthLog(PlatformModel):
    """System health check snapshots."""

    status = models.CharField(max_length=20, choices=[
        ("healthy", "Healthy"), ("degraded", "Degraded"), ("down", "Down"),
    ])
    database_ok = models.BooleanField(default=True)
    redis_ok = models.BooleanField(default=True)
    celery_ok = models.BooleanField(default=True)
    details = models.JSONField(default=dict, blank=True)
    response_time_ms = models.PositiveIntegerField(default=0)


class PlatformMetrics(PlatformModel):
    """Singleton platform operational metrics for dashboards."""

    storage_used_mb = models.PositiveIntegerField(default=0)
    storage_cap_mb = models.PositiveIntegerField(default=1024)
    failed_jobs_24h = models.PositiveIntegerField(default=0)
    uptime_percent = models.DecimalField(max_digits=6, decimal_places=3, default=100)
    customer_satisfaction_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    feature_adoption_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    support_resolution_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name_plural = "Platform metrics"

    @classmethod
    def get_current(cls) -> "PlatformMetrics":
        metrics, _ = cls.objects.get_or_create(pk=1)
        return metrics