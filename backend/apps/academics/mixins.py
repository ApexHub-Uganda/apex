"""View mixins for academic data scoping and singleton records."""
from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from apps.academics.scoping import filter_queryset_for_user, should_scope_to_assignments
from apps.academics.singleton import (
    assert_active_term_for_timetable,
    assert_can_create_academic_year,
    assert_can_create_examination_session,
    assert_can_create_term,
    build_singleton_list_meta,
)
from apps.tenants.role_permissions import user_is_school_admin


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


class SchoolAdminManageSingletonMixin:
    """
    Singleton periods: create remains locked while one is active (all roles).
    School admins always retain full update/delete on these records.
    """

    def _user_can_manage_singleton_records(self) -> bool:
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_super_admin", False) or user_is_school_admin(user):
            return True
        # Other roles with module write may still update when feature permissions allow
        # (enforced by RequiresFeature on the viewset). Do not block them here.
        return True

    def perform_update(self, serializer):
        if not self._user_can_manage_singleton_records():
            raise PermissionDenied("You do not have permission to edit this record.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not self._user_can_manage_singleton_records():
            raise PermissionDenied("You do not have permission to delete this record.")
        super().perform_destroy(instance)


class AcademicYearSingletonMixin(SchoolAdminManageSingletonMixin, AcademicSingletonListMixin):
    singleton_kind = "academic_year"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_academic_year(tenant)
        super().perform_create(serializer)


class TermSingletonMixin(SchoolAdminManageSingletonMixin, AcademicSingletonListMixin):
    singleton_kind = "term"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_term(tenant)
        super().perform_create(serializer)


class ExaminationSessionSingletonMixin(SchoolAdminManageSingletonMixin, AcademicSingletonListMixin):
    singleton_kind = "examination_session"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_examination_session(tenant)
        super().perform_create(serializer)


class TimetableActiveTermMixin(AcademicSingletonListMixin):
    singleton_kind = "term"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_active_term_for_timetable(tenant)
        super().perform_create(serializer)