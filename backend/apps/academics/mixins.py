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
        # Exam periods: DoS may also edit / end / delete (school-wide exam calendar).
        if not can_mutate and self.singleton_kind == "examination_session":
            from apps.core.constants import UserRole, normalize_role

            role = normalize_role(getattr(request.user, "role", ""))
            can_mutate = role == UserRole.DIRECTOR_OF_STUDIES
        meta["school_admin_can_manage"] = can_mutate
        # Non-admins with create permission may create; only managers may edit/delete/status.
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
    - After creation, school admin (and for exam periods, DoS) may update, delete,
      or change status. Other users remain read-only.
    """

    # Override on mixins that should also allow DoS (exam sessions).
    allow_dos_mutate: bool = False

    def _user_is_school_admin(self) -> bool:
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, "is_super_admin", False) or user_is_school_admin(user))

    def _user_can_mutate_singleton(self) -> bool:
        if self._user_is_school_admin():
            return True
        if not self.allow_dos_mutate:
            return False
        from apps.core.constants import UserRole, normalize_role

        role = normalize_role(getattr(self.request.user, "role", ""))
        return role == UserRole.DIRECTOR_OF_STUDIES

    def _assert_school_admin_mutate(self, *, action: str = "change") -> None:
        if self._user_can_mutate_singleton():
            return
        who = "a school admin or Director of Studies" if self.allow_dos_mutate else "a school admin"
        raise PermissionDenied(
            f"Only {who} can {action} academic years, terms, or exam periods "
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
    allow_dos_mutate = True

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_can_create_examination_session(tenant)
        super().perform_create(serializer)
        instance = serializer.instance
        self._after_exam_period_saved(instance, created=True)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._after_exam_period_saved(serializer.instance, created=False)

    def _after_exam_period_saved(self, instance, *, created: bool) -> None:
        """Auto-open planned periods in window and provision mark sheets for teachers."""
        from apps.examinations.constants import (
            EXAMINATION_SESSION_ACTIVE,
            EXAMINATION_SESSION_CLOSED,
            EXAMINATION_SESSION_PLANNED,
        )
        from apps.examinations.marks_scoping import provision_period_mark_sheets
        from django.utils import timezone

        if instance is None or instance.status == EXAMINATION_SESSION_CLOSED:
            return
        today = timezone.now().date()
        # Auto-activate planned sessions once their window has started
        if (
            instance.status == EXAMINATION_SESSION_PLANNED
            and instance.start_date
            and instance.start_date <= today
            and (not instance.end_date or instance.end_date >= today)
        ):
            instance.status = EXAMINATION_SESSION_ACTIVE
            instance.save(update_fields=["status", "updated_at"])

        if instance.status in {EXAMINATION_SESSION_ACTIVE, EXAMINATION_SESSION_PLANNED}:
            if not instance.end_date or instance.end_date >= today:
                provision_period_mark_sheets(
                    tenant=instance.tenant,
                    period=instance,
                    actor=self.request.user,
                )


class TimetableActiveTermMixin(AcademicSingletonListMixin):
    singleton_kind = "term"

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        assert_active_term_for_timetable(tenant)
        super().perform_create(serializer)
