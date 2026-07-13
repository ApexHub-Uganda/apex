"""Dashboard header context — year, term, teacher assignments."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Subject, Term, Timetable
from apps.analytics.dashboard_context import build_dashboard_header_context
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def dash_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Dash Plan", slug="dash-plan", max_students=500)
    assign_plan_features(plan, [
        "dashboard_analytics", "classes", "subjects", "terms", "academic_years",
        "timetables",
    ])
    return plan


@pytest.fixture
def dash_tenant(db, dash_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Dash School",
        code="DASH",
        email="dash@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=dash_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def teacher_staff(db, dash_tenant):
    return onboard_staff(
        dash_tenant,
        data={
            "first_name": "Dash",
            "last_name": "Teacher",
            "email": "dash.teacher@test.edu",
            "phone": "+254700000401",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def dash_setup(db, dash_tenant, teacher_staff):
    year = AcademicYear.objects.create(
        tenant=dash_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=dash_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    assigned = Class.objects.create(
        tenant=dash_tenant, name="Grade 4", code="G4", academic_year=year,
    )
    Class.objects.create(
        tenant=dash_tenant, name="Grade 8", code="G8", academic_year=year,
    )
    Subject.objects.create(tenant=dash_tenant, name="Mathematics", code="MTC")
    subject = Subject.objects.create(tenant=dash_tenant, name="Science", code="SCI")
    teacher = teacher_staff.teacher_profile
    Timetable.objects.create(
        tenant=dash_tenant,
        school_class=assigned,
        subject=subject,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    return {
        "teacher_user": teacher_staff.user,
    }


@pytest.mark.django_db
class TestDashboardHeaderContext:
    def test_teacher_gets_year_term_class_and_subject_codes(self, dash_tenant, dash_setup):
        ctx = build_dashboard_header_context(tenant=dash_tenant, user=dash_setup["teacher_user"])
        assert ctx["academic_year"]["name"] == "2026"
        assert ctx["current_term"]["name"] == "Term 1"
        assert ctx["assigned_classes"] == ["Grade 4"]
        assert ctx["subject_codes"] == ["SCI"]

    def test_school_admin_gets_only_calendar(self, dash_tenant, dash_setup, db):
        from apps.accounts.models import User

        admin = User.objects.create_user(
            email="dash.admin@test.edu",
            password="TestPass@2026",
            first_name="Dash",
            last_name="Admin",
            role=UserRole.SCHOOL_ADMIN,
            tenant=dash_tenant,
            is_email_verified=True,
        )
        ctx = build_dashboard_header_context(tenant=dash_tenant, user=admin)
        assert ctx["academic_year"]["name"] == "2026"
        assert ctx["current_term"]["name"] == "Term 1"
        assert ctx["assigned_classes"] is None
        assert ctx["subject_codes"] is None