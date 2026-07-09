"""View mixins for HR portal roles."""
from __future__ import annotations

from apps.hr.scoping import filter_hr_queryset_for_user


class HRScopeMixin:
    """Restrict HR querysets to users with HR portal access."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        return filter_hr_queryset_for_user(qs, user)