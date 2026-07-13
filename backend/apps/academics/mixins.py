"""View mixins for academic data scoping and singleton records."""
from __future__ import annotations



from apps.academics.scoping import filter_queryset_for_user, should_scope_to_assignments
from apps.academics.singleton import (
    assert_active_term_for_timetable,
    assert_can_create_academic_year,
    assert_can_create_term,
    build_singleton_list_meta,
)


class AcademicScopeMixin:
    """Restrict querysets to assignments for read-only / non-school-wide users."""

    academic_scope_feature: str | None = None

    def get_academic_scope_feature(self) -> str | None:
        return self.academic_scope_feature or getattr(self, "required_feature_key", None)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        feature = self.get_academic_scope_feature()
        if not should_scope_to_assignments(user, feature_key=feature):
            return qs
        return filter_queryset_for_user(qs, user)


class AcademicSingletonListMixin:
    """Attach active-record metadata to list responses."""

    singleton_kind: str = ""

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not self.singleton_kind:
            return response
        tenant = getattr(request.user, "tenant", None)
        meta = build_singleton_list_meta(tenant=tenant, kind=self.singleton_kind)
        if isinstance(response.data, dict):
            response.data["meta"] = meta
        return response


class AcademicYearSingletonMixin(AcademicSingletonListMixin):
    singleton_kind = "academic_year"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_academic_year(tenant)
        super().perform_create(serializer)


class TermSingletonMixin(AcademicSingletonListMixin):
    singleton_kind = "term"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_term(tenant)
        super().perform_create(serializer)


class TimetableActiveTermMixin(AcademicSingletonListMixin):
    singleton_kind = "term"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_active_term_for_timetable(tenant)
        super().perform_create(serializer)