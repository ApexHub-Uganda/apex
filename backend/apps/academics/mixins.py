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
    Once a year/term is in use (current, or has published timetable / dependent data),
    only school admins may edit, delete, or end it.
    """

    def _user_is_school_admin(self) -> bool:
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, "is_super_admin", False) or user_is_school_admin(user))

    def _record_is_in_use(self, instance) -> bool:
        """True when non-admins must not mutate this year/term."""
        model_name = instance.__class__.__name__
        if model_name == "AcademicYear":
            if getattr(instance, "is_current", False):
                return True
            # Any terms, classes, or published timetables under this year
            if instance.terms.filter(is_deleted=False).exists():
                return True
            from apps.academics.models import TimetableSchedule
            if TimetableSchedule.objects.filter(
                tenant=instance.tenant_id, academic_year=instance, is_deleted=False,
            ).exclude(status="archived").exists():
                return True
            return False
        if model_name == "Term":
            if getattr(instance, "is_current", False):
                return True
            from apps.academics.models import Timetable, TimetableSchedule
            if TimetableSchedule.objects.filter(
                tenant=instance.tenant_id, term=instance, is_deleted=False,
            ).exclude(status="archived").exists():
                return True
            if Timetable.objects.filter(
                tenant=instance.tenant_id, term=instance, is_deleted=False,
            ).exists():
                return True
            return False
        return False

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance is not None and self._record_is_in_use(instance) and not self._user_is_school_admin():
            raise PermissionDenied(
                "This record is already in use. Only a school admin can edit or end it."
            )
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if self._record_is_in_use(instance) and not self._user_is_school_admin():
            raise PermissionDenied(
                "This record is already in use. Only a school admin can delete or end it."
            )
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