"""Outbound messaging provider adapters for platform broadcasts."""

from apps.platform.services.providers.registry import (
    get_email_provider,
    get_integration_channel_status,
    get_sms_provider,
    get_whatsapp_provider,
)

__all__ = [
    "get_email_provider",
    "get_sms_provider",
    "get_whatsapp_provider",
    "get_integration_channel_status",
]