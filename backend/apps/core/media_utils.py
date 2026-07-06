"""Shared helpers for resolving uploaded file URLs in API responses."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.core.files import File
    from rest_framework.request import Request


def resolve_media_url(request: Request | None, file_field: File | None) -> str | None:
    if not file_field:
        return None
    try:
        url = file_field.url
    except (ValueError, AttributeError):
        return None
    if request is not None:
        return request.build_absolute_uri(url)
    return url