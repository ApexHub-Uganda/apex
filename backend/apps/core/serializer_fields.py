"""Reusable DRF serializer fields."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.email_validation import validate_deliverable_email


class DeliverableEmailField(serializers.EmailField):
    """Email field that rejects placeholder and dummy addresses."""

    def __init__(self, *args, required=True, allow_blank=False, **kwargs):
        super().__init__(*args, required=required, allow_blank=allow_blank, **kwargs)
        self._deliverable_required = required and not allow_blank

    def to_internal_value(self, data):
        if data in (None, "") and not self._deliverable_required:
            return ""
        value = super().to_internal_value(data)
        error = validate_deliverable_email(value, required=self._deliverable_required)
        if error:
            raise serializers.ValidationError(error)
        return value