"""Default per-feature permissions for academic portal roles."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_feature_defaults import (
    get_default_feature_permission,
    merge_class_teacher_feature_permissions,
)
from apps.tenants.role_permissions import get_user_feature_permissions


@pytest.fixture
def academic_roles_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Academic Roles", slug="academic-roles", max_students=500)
    assign_plan_features(plan, [
        "teacher_workspace", "hod_workspace", "dos_workspace", "class_teacher_tools",
        "classes", "subjects", "terms", "homework", "assignments", "timetables",
        "marks_entry", "assessment_management", "marks_approval", "lesson_attendance",
        "class_notices", "discipline_remarks", "class_report_cards",
        "examination_management", "report_cards", "dashboard_analytics",
    ])
    return plan


@pytest.fixture
def academic_roles_tenant(db, academic_roles_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Academic Roles School",
        code="AROLE",
        email="arole@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=academic_roles_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def portal_teacher(db, academic_roles_tenant):
    return onboard_staff(
        academic_roles_tenant,
        data={
            "first_name": "Portal",
            "last_name": "Teacher",
            "email": "portal.teacher@test.edu",
            "phone": "+254700000101",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.mark.django_db
class TestRoleFeatureDefaults:
    def test_teacher_default_permissions(self):
        assert get_default_feature_permission(UserRole.TEACHER, "teacher_workspace") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "classes") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "academic_years") == {
            "can_read": False, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "marks_entry") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "marks_approval") == {
            "can_read": False, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "class_teacher_tools") == {
            "can_read": False, "can_write": False,
        }

    def test_hod_default_permissions(self):
        assert get_default_feature_permission(UserRole.HEAD_OF_DEPARTMENT, "hod_workspace") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.HEAD_OF_DEPARTMENT, "marks_approval") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.HEAD_OF_DEPARTMENT, "teacher_workspace") == {
            "can_read": False, "can_write": False,
        }

    def test_dos_default_permissions(self):
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "dos_workspace") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "teacher_assignments") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "teacher_workspace") == {
            "can_read": False, "can_write": False,
        }
        # DoS reads marks/results; may generate/print report cards; never writes marks
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "marks_entry") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "grade_calculation") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.DIRECTOR_OF_STUDIES, "report_cards") == {
            "can_read": True, "can_write": True,
        }

    def test_teacher_cannot_print_report_cards_by_default(self):
        assert get_default_feature_permission(UserRole.TEACHER, "report_cards") == {
            "can_read": False, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.TEACHER, "marks_entry") == {
            "can_read": True, "can_write": True,
        }

    def test_class_teacher_role_default_permissions(self):
        assert get_default_feature_permission(UserRole.CLASS_TEACHER, "class_teacher_tools") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.CLASS_TEACHER, "class_notices") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.CLASS_TEACHER, "discipline_remarks") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.CLASS_TEACHER, "teacher_workspace") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.CLASS_TEACHER, "marks_entry") == {
            "can_read": True, "can_write": True,
        }

    def test_class_teacher_overlay_elevates_features(self):
        base = {
            "class_teacher_tools": {"can_read": False, "can_write": False},
            "class_notices": {"can_read": False, "can_write": False},
            "marks_entry": {"can_read": True, "can_write": True},
        }
        merged = merge_class_teacher_feature_permissions(base, is_class_teacher=True)
        assert merged["class_teacher_tools"]["can_read"] is True
        assert merged["class_teacher_tools"]["can_write"] is True
        assert merged["class_notices"]["can_write"] is True
        assert merged["marks_entry"]["can_write"] is True

    def test_teacher_effective_permissions_use_defaults(self, academic_roles_tenant, portal_teacher):
        perms = get_user_feature_permissions(academic_roles_tenant, portal_teacher.user)
        assert perms["teacher_workspace"]["can_read"] is True
        assert perms["classes"]["can_read"] is True
        assert perms["classes"]["can_write"] is False
        assert perms["marks_entry"]["can_write"] is True
        assert perms.get("academic_years", {}).get("can_read") in (None, False)

    def test_class_teacher_assignment_elevates_features(
        self, academic_roles_tenant, portal_teacher,
    ):
        year = AcademicYear.objects.create(
            tenant=academic_roles_tenant,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        school_class = Class.objects.create(
            tenant=academic_roles_tenant,
            name="Grade 4",
            code="G4",
            academic_year=year,
            class_teacher=portal_teacher.teacher_profile,
        )
        assert school_class.class_teacher_id == portal_teacher.teacher_profile.id

        perms = get_user_feature_permissions(academic_roles_tenant, portal_teacher.user)
        assert perms["class_teacher_tools"]["can_read"] is True
        assert perms["class_teacher_tools"]["can_write"] is True
        assert perms["class_notices"]["can_write"] is True