"""Audit logging models."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable audit trail for sensitive actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="audit_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs",
    )
    action = models.CharField(max_length=50, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "action", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.resource_type} by {self.user_id}"