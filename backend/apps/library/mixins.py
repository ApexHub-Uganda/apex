"""View mixins for library portal roles."""
from __future__ import annotations

from apps.library.scoping import filter_library_queryset_for_user


class LibraryScopeMixin:
    """Restrict library querysets to users with library portal access."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        return filter_library_queryset_for_user(qs, user)