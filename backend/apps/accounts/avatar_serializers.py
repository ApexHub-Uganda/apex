"""Shared avatar fields for user serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.avatar_service import resolve_avatar_url, user_has_avatar


class AvatarFieldsMixin:
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()

    def get_avatar_url(self, obj) -> str | None:
        request = self.context.get("request")
        return resolve_avatar_url(obj, request)

    def get_has_avatar(self, obj) -> bool:
        return user_has_avatar(obj)