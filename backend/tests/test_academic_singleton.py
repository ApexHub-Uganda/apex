"""Singleton enforcement for academic year, term, and timetable creation."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Term
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def singleton_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Singleton Plan", slug="singleton-plan", max_students=500)
    assign_plan_features(plan, [
        "academic_years", "terms", "timetables", "classes", "subjects",
    ])
    return plan


@pytest.fixture
def singleton_tenant(db, singleton_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Singleton School",
        code="SING",
        email="singleton@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=singleton_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def dos_user(db, singleton_tenant):
    staff = onboard_staff(
        singleton_tenant,
        data={
            "first_name": "First",
            "last_name": "DOS",
            "email": "dos1@test.edu",
            "phone": "+254700000301",
            "portal_role": UserRole.DIRECTOR_OF_STUDIES,
            "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.fixture
def second_dos_user(db, singleton_tenant):
    staff = onboard_staff(
        singleton_tenant,
        data={
            "first_name": "Second",
            "last_name": "DOS",
            "email": "dos2@test.edu",
            "phone": "+254700000302",
            "portal_role": UserRole.DIRECTOR_OF_STUDIES,
            "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.fixture
def active_year_and_term(db, singleton_tenant):
    year = AcademicYear.objects.create(
        tenant=singleton_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=singleton_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    return {"year": year, "term": term}


@pytest.mark.django_db
class TestAcademicSingleton:
    def test_second_user_cannot_create_academic_year_while_active(
        self, api_client, dos_user, second_dos_user, active_year_and_term,
    ):
        api_client.force_authenticate(user=second_dos_user)
        response = api_client.post(
            "/api/v1/academics/years/",
            {
                "name": "2027",
                "start_date": "2027-01-01",
                "end_date": "2027-12-31",
                "is_current": False,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "still active" in str(response.data).lower()

    def test_second_user_cannot_create_term_while_active(
        self, api_client, second_dos_user, active_year_and_term,
    ):
        year = active_year_and_term["year"]
        api_client.force_authenticate(user=second_dos_user)
        response = api_client.post(
            "/api/v1/academics/terms/",
            {
                "name": "Term 2",
                "academic_year": str(year.id),
                "term_number": 2,
                "start_date": "2026-05-01",
                "end_date": "2026-08-01",
                "is_current": False,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "still active" in str(response.data).lower()

    def test_list_includes_creation_locked_meta(
        self, api_client, dos_user, active_year_and_term,
    ):
        api_client.force_authenticate(user=dos_user)
        response = api_client.get("/api/v1/academics/terms/")
        assert response.status_code == 200
        meta = response.data.get("meta") or response.data.get("data", {}).get("meta")
        assert meta is not None
        assert meta["creation_locked"] is True
        assert meta["active_record"]["name"] == "Term 1"
        assert meta["singleton_type"] == "term"

    def test_academic_year_list_meta(
        self, api_client, dos_user, active_year_and_term,
    ):
        api_client.force_authenticate(user=dos_user)
        response = api_client.get("/api/v1/academics/years/")
        assert response.status_code == 200
        meta = response.data.get("meta") or response.data.get("data", {}).get("meta")
        assert meta is not None
        assert meta["creation_locked"] is True
        assert meta["active_record"]["name"] == "2026"

    def test_timetable_create_blocked_without_active_term(
        self, api_client, dos_user, singleton_tenant,
    ):
        year = AcademicYear.objects.create(
            tenant=singleton_tenant,
            name="2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=False,
        )
        Term.objects.create(
            tenant=singleton_tenant,
            academic_year=year,
            name="Old Term",
            term_number=1,
            start_date=date(2025, 1, 10),
            end_date=date(2025, 4, 10),
            is_current=False,
        )
        from apps.academics.models import Class, Subject

        school_class = Class.objects.create(
            tenant=singleton_tenant, name="Grade 1", code="G1", academic_year=year,
        )
        subject = Subject.objects.create(tenant=singleton_tenant, name="Math", code="M1")
        teacher_staff = onboard_staff(
            singleton_tenant,
            data={
                "first_name": "Slot",
                "last_name": "Teacher",
                "email": "slot.teacher@test.edu",
                "phone": "+254700000303",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2026-01-01",
            },
        )
        teacher = teacher_staff.teacher_profile

        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/academics/timetables/",
            {
                "school_class": str(school_class.id),
                "subject": str(subject.id),
                "teacher": str(teacher.id),
                "day_of_week": 0,
                "start_time": "08:00",
                "end_time": "09:00",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "no active academic term" in str(response.data).lower()

    def test_can_create_after_active_year_ends(
        self, api_client, second_dos_user, singleton_tenant,
    ):
        AcademicYear.objects.create(
            tenant=singleton_tenant,
            name="2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=False,
        )
        api_client.force_authenticate(user=second_dos_user)
        response = api_client.post(
            "/api/v1/academics/years/",
            {
                "name": "2026",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "is_current": True,
            },
            format="json",
        )
        assert response.status_code in (200, 201)