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

# Academic years, terms, and exam periods: non-admins create then read-only.
PERIOD_SINGLETON_KINDS = frozenset({"academic_year", "term", "examination_session"})


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
        can_mutate = bool(
            getattr(request.user, "is_super_admin", False)
            or user_is_school_admin(request.user)
        )
        meta["school_admin_can_manage"] = can_mutate
        # Non-admins with create permission may create; only school admin may edit/delete/status.
        meta["can_mutate"] = can_mutate
        meta["can_edit"] = can_mutate
        meta["can_delete"] = can_mutate
        if isinstance(response.data, dict):
            response.data["meta"] = meta
        return response


class SchoolAdminManageSingletonMixin:
    """
    Academic year / term / exam period lifecycle.

    - Any role with feature write may **create** (when creation is not locked).
    - After creation, only the **school admin** may update, delete, or change status
      (is_current, status, dates, names, etc.). Other users remain read-only.
    """

    def _user_is_school_admin(self) -> bool:
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, "is_super_admin", False) or user_is_school_admin(user))

    def _assert_school_admin_mutate(self, *, action: str = "change") -> None:
        if self._user_is_school_admin():
            return
        raise PermissionDenied(
            f"Only a school admin can {action} academic years, terms, or exam periods "
            "after they are created. You may create a new one when the current period ends."
        )

    def perform_update(self, serializer):
        self._assert_school_admin_mutate(action="edit or change the status of")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._assert_school_admin_mutate(action="delete")
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
