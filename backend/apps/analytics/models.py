"""Analytics models (mostly computed; minimal persistence)."""
from apps.core.models import BaseModel
from django.db import models


class DashboardSnapshot(BaseModel):
    """Cached dashboard metrics snapshot."""

    snapshot_type = models.CharField(max_length=30, choices=[
        ("school_admin", "School Admin"),
        ("super_admin", "Super Admin"),
    ])
    metrics = models.JSONField(default=dict)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "snapshot_type", "created_at"])]