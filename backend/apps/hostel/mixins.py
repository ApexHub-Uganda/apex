"""Hostel view scoping mixin."""
from __future__ import annotations

from apps.hostel.scoping import filter_by_managed_hostels, filter_hostel_queryset_for_user


class HostelScopeMixin:
    hostel_scope_field = "id"
    hostel_scope_path = ""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if self.hostel_scope_path:
            return filter_by_managed_hostels(qs, user, hostel_path=self.hostel_scope_path)
        return filter_hostel_queryset_for_user(qs, user, hostel_field=self.hostel_scope_field)