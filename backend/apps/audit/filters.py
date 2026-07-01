"""Audit log filters."""
from __future__ import annotations

import django_filters

from apps.audit.models import AuditLog


class AuditLogFilterSet(django_filters.FilterSet):
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    action = django_filters.CharFilter(lookup_expr="iexact")
    resource_type = django_filters.CharFilter(lookup_expr="iexact")
    category = django_filters.CharFilter(method="filter_category")
    tenant = django_filters.UUIDFilter(field_name="tenant_id")
    status = django_filters.CharFilter(method="filter_status")
    user_email = django_filters.CharFilter(field_name="user__email", lookup_expr="icontains")

    class Meta:
        model = AuditLog
        fields = ["action", "resource_type", "tenant"]

    CATEGORY_MAP = {
        "authentication": ["auth", "login", "logout", "session"],
        "schools": ["tenant", "school"],
        "billing": ["subscription", "payment", "plan", "invoice"],
        "users": ["user", "account", "profile"],
        "academics": ["student", "staff", "class", "attendance", "academic"],
        "communication": ["broadcast", "notification", "email", "sms"],
        "system": ["platform", "settings", "health"],
    }

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        key = value.lower()
        types = self.CATEGORY_MAP.get(key, [key])
        return queryset.filter(resource_type__in=types)

    def filter_status(self, queryset, name, value):
        if value == "success":
            return queryset.filter(status_code__gte=200, status_code__lt=400)
        if value == "failed":
            return queryset.filter(status_code__gte=400)
        if value == "unknown":
            return queryset.filter(status_code__isnull=True)
        return queryset