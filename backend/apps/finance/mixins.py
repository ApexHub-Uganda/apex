"""View mixins for finance portal roles."""
from __future__ import annotations

from apps.finance.scoping import filter_finance_queryset_for_user


class FinanceScopeMixin:
    """Restrict finance querysets to users with finance portal access."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        return filter_finance_queryset_for_user(qs, user)