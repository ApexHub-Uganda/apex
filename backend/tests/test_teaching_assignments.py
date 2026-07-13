"""Teaching assignment API — teacher / class / subject staffing."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Subject, TeachingAssignment, Timetable
from apps.academics.scoping import get_academic_context
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def ta_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="TA Plan", slug="ta-plan", max_students=500)
    assign_plan_features(plan, [
        "subject_assignment", "teacher_assignments", "classes", "subjects",
        "academic_years", "terms", "timetables",
    ])
    return plan


@pytest.fixture
def ta_tenant(db, ta_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="TA School",
        code="TASCH",
        email="ta@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=ta_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def dos_user(db, ta_tenant):
    staff = onboard_staff(
        ta_tenant,
        data={
            "first_name": "Assign",
            "last_name": "DOS",
            "email": "assign.dos@test.edu",
            "phone": "+254700000501",
            "portal_role": UserRole.DIRECTOR_OF_STUDIES,
            "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.fixture
def teacher_staff(db, ta_tenant):
    return onboard_staff(
        ta_tenant,
        data={
            "first_name": "Teach",
            "last_name": "One",
            "email": "teach.one@test.edu",
            "phone": "+254700000502",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def ta_setup(db, ta_tenant, teacher_staff):
    year = AcademicYear.objects.create(
        tenant=ta_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=ta_tenant, name="Grade 5", code="G5", academic_year=year,
    )
    math = Subject.objects.create(tenant=ta_tenant, name="Mathematics", code="MTC")
    eng = Subject.objects.create(tenant=ta_tenant, name="English", code="ENG")
    return {
        "year": year,
        "class": school_class,
        "math": math,
        "eng": eng,
        "teacher_user": teacher_staff.user,
        "teacher": teacher_staff.teacher_profile,
    }


@pytest.mark.django_db
class TestTeachingAssignments:
    def test_bulk_assign_creates_rows(self, api_client, dos_user, ta_setup):
        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/academics/teaching-assignments/bulk-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["math"].id), str(ta_setup["eng"].id)],
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data.get("created_count", 0) == 2
        assert TeachingAssignment.objects.filter(
            teacher=ta_setup["teacher"],
            school_class=ta_setup["class"],
            is_active=True,
        ).count() == 2

    def test_teacher_subjects_synced(self, api_client, dos_user, ta_setup):
        api_client.force_authenticate(user=dos_user)
        api_client.post(
            "/api/v1/academics/teaching-assignments/bulk-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["math"].id)],
            },
            format="json",
        )
        ta_setup["teacher"].refresh_from_db()
        codes = set(ta_setup["teacher"].subjects.values_list("code", flat=True))
        assert codes == {"MTC"}

    def test_teacher_list_scoped_to_own_assignments(self, api_client, dos_user, ta_setup, ta_tenant):
        from apps.tenants.models import SchoolRoleFeaturePermission
        from apps.tenants.role_permissions import invalidate_role_permissions_cache

        SchoolRoleFeaturePermission.objects.create(
            tenant=ta_tenant,
            role=UserRole.TEACHER,
            feature_key="subject_assignment",
            can_read=True,
            can_write=False,
        )
        invalidate_role_permissions_cache(ta_tenant.id)

        other_teacher = onboard_staff(
            ta_setup["class"].tenant,
            data={
                "first_name": "Other",
                "last_name": "Teacher",
                "email": "other.teacher@test.edu",
                "phone": "+254700000503",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2026-01-01",
            },
        )
        api_client.force_authenticate(user=dos_user)
        api_client.post(
            "/api/v1/academics/teaching-assignments/bulk-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["math"].id)],
            },
            format="json",
        )
        api_client.post(
            "/api/v1/academics/teaching-assignments/bulk-assign/",
            {
                "teacher": str(other_teacher.teacher_profile.id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["eng"].id)],
            },
            format="json",
        )
        api_client.force_authenticate(user=ta_setup["teacher_user"])
        response = api_client.get("/api/v1/academics/teaching-assignments/")
        assert response.status_code == 200
        results = response.data.get("results") or response.data.get("data", {}).get("results", [])
        assert len(results) == 1
        assert results[0]["subject_code"] == "MTC"

    def test_scoping_uses_teaching_assignment(self, ta_tenant, ta_setup):
        TeachingAssignment.objects.create(
            tenant=ta_tenant,
            teacher=ta_setup["teacher"],
            school_class=ta_setup["class"],
            subject=ta_setup["math"],
            academic_year=ta_setup["year"],
            is_active=True,
        )
        ctx = get_academic_context(ta_setup["teacher_user"])
        assert ta_setup["math"].id in ctx.assigned_subject_ids
        assert ta_setup["class"].id in ctx.assigned_class_ids
        assert (ta_setup["math"].id, ta_setup["class"].id) in ctx.teaching_pairs

    def test_form_options_lists_teachers_and_subject_codes(self, api_client, dos_user, ta_setup):
        api_client.force_authenticate(user=dos_user)
        response = api_client.get("/api/v1/academics/teaching-assignments/form-options/")
        assert response.status_code == 200
        data = response.data.get("data") or response.data
        assert any(t["label"] for t in data["teachers"])
        assert any(s["code"] == "MTC" for s in data["subjects"])

    def test_sync_teacher_across_different_classes(self, api_client, dos_user, ta_setup):
        g6 = Class.objects.create(
            tenant=ta_setup["class"].tenant,
            name="Grade 6",
            code="G6",
            academic_year=ta_setup["year"],
        )
        physics = Subject.objects.create(
            tenant=ta_setup["class"].tenant,
            name="Physics",
            code="PHY",
        )
        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/academics/teaching-assignments/sync-teacher/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "assignments": [
                    {
                        "school_class": str(ta_setup["class"].id),
                        "subject": str(ta_setup["math"].id),
                    },
                    {
                        "school_class": str(g6.id),
                        "subject": str(physics.id),
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(response.data["data"]) == 2
        assert TeachingAssignment.objects.filter(
            teacher=ta_setup["teacher"],
            is_active=True,
            is_deleted=False,
        ).count() == 2

        ta_setup["teacher"].refresh_from_db()
        codes = set(ta_setup["teacher"].subjects.values_list("code", flat=True))
        assert codes == {"MTC", "PHY"}

    def test_sync_assign_manages_multiple_subjects(self, api_client, dos_user, ta_setup):
        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/academics/teaching-assignments/sync-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["math"].id), str(ta_setup["eng"].id)],
                "notes": "Combined",
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(response.data["data"]) == 2
        assert TeachingAssignment.objects.filter(
            teacher=ta_setup["teacher"],
            school_class=ta_setup["class"],
            is_active=True,
        ).count() == 2

        response = api_client.post(
            "/api/v1/academics/teaching-assignments/sync-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["eng"].id)],
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["subject_code"] == "ENG"
        assert TeachingAssignment.objects.filter(
            teacher=ta_setup["teacher"],
            school_class=ta_setup["class"],
            is_active=True,
            is_deleted=False,
        ).count() == 1

        ta_setup["teacher"].refresh_from_db()
        codes = set(ta_setup["teacher"].subjects.values_list("code", flat=True))
        assert codes == {"ENG"}

    def test_update_assignment_changes_subject(self, api_client, dos_user, ta_setup):
        api_client.force_authenticate(user=dos_user)
        create_resp = api_client.post(
            "/api/v1/academics/teaching-assignments/bulk-assign/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject_ids": [str(ta_setup["math"].id)],
                "notes": "Form 5",
            },
            format="json",
        )
        assert create_resp.status_code == 201
        assignment_id = create_resp.data["data"][0]["id"]

        response = api_client.patch(
            f"/api/v1/academics/teaching-assignments/{assignment_id}/",
            {
                "teacher": str(ta_setup["teacher"].id),
                "school_class": str(ta_setup["class"].id),
                "subject": str(ta_setup["eng"].id),
                "notes": "Updated note",
            },
            format="json",
        )
        assert response.status_code == 200
        body = response.data.get("data") or response.data
        assert body["subject_code"] == "ENG"
        assert body["notes"] == "Updated note"

        ta_setup["teacher"].refresh_from_db()
        codes = set(ta_setup["teacher"].subjects.values_list("code", flat=True))
        assert codes == {"ENG"}