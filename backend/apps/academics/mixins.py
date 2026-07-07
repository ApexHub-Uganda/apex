"""View mixins for academic data scoping."""
from __future__ import annotations

from apps.academics.scoping import filter_queryset_for_user


class AcademicScopeMixin:
    """Restrict list/detail querysets to the user's academic assignments."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        return filter_queryset_for_user(qs, user)