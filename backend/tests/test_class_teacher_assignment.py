"""Class teacher assignment — dual-role access and stream heads."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Stream
from apps.accounts.models import User, UserRoleAssignment
from apps.core.constants import UserRole
from apps.staff.models import Staff, Teacher
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def ct_plan(plan):
    assign_plan_features(plan, [
        "classes", "streams", "teacher_assignments", "subject_assignment",
        "class_teacher_tools", "staff_management", "dos_workspace",
        "academic_years", "terms",
    ])
    return plan


@pytest.fixture
def ct_setup(db, tenant, school_admin, ct_plan):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    c1 = Class.objects.create(
        tenant=tenant, name="S.1", code="S1", academic_year=year, capacity=40,
    )
    stream = Stream.objects.create(tenant=tenant, school_class=c1, name="East", capacity=20)

    staff = Staff.objects.create(
        tenant=tenant, employee_id="T001", first_name="Jane", last_name="Teacher",
        email="jane.ct@test.edu", portal_role=UserRole.TEACHER, status="active",
        has_portal_access=True, date_joined="2026-01-01",
    )
    teacher_user = User.objects.create_user(
        email="jane.ct@test.edu", password="pass12345", role=UserRole.TEACHER,
        tenant=tenant, first_name="Jane", last_name="Teacher", is_staff=True,
    )
    staff.user = teacher_user
    staff.save(update_fields=["user"])
    teacher = Teacher.objects.create(tenant=tenant, staff=staff, is_class_teacher=False)

    return {
        "tenant": tenant,
        "admin": school_admin,
        "teacher": teacher,
        "teacher_user": teacher_user,
        "class": c1,
        "stream": stream,
        "year": year,
    }


@pytest.mark.django_db
class TestClassTeacherAssignmentAPI:
    def test_assign_whole_class_sets_flag_and_dual_role(self, ct_setup):
        client = APIClient()
        client.force_authenticate(user=ct_setup["admin"])
        response = client.post(
            "/api/v1/academics/class-teacher-assignments/assign/",
            {
                "school_class": str(ct_setup["class"].id),
                "teacher": str(ct_setup["teacher"].id),
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        ct_setup["class"].refresh_from_db()
        ct_setup["teacher"].refresh_from_db()
        assert ct_setup["class"].class_teacher_id == ct_setup["teacher"].id
        assert ct_setup["teacher"].is_class_teacher is True

        dual = UserRoleAssignment.objects.filter(
            user=ct_setup["teacher_user"],
            role=UserRole.CLASS_TEACHER,
            is_active=True,
        ).first()
        assert dual is not None
        assert dual.source == "class_assignment"
        ct_setup["teacher_user"].refresh_from_db()
        assert ct_setup["teacher_user"].role == UserRole.TEACHER

    def test_assign_stream_head(self, ct_setup):
        client = APIClient()
        client.force_authenticate(user=ct_setup["admin"])
        response = client.post(
            "/api/v1/academics/class-teacher-assignments/assign/",
            {
                "school_class": str(ct_setup["class"].id),
                "stream": str(ct_setup["stream"].id),
                "teacher": str(ct_setup["teacher"].id),
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        ct_setup["stream"].refresh_from_db()
        ct_setup["teacher"].refresh_from_db()
        assert ct_setup["stream"].class_teacher_id == ct_setup["teacher"].id
        assert ct_setup["teacher"].is_class_teacher is True

    def test_unassign_clears_flag_and_auto_dual_role(self, ct_setup):
        client = APIClient()
        client.force_authenticate(user=ct_setup["admin"])
        client.post(
            "/api/v1/academics/class-teacher-assignments/assign/",
            {
                "school_class": str(ct_setup["class"].id),
                "teacher": str(ct_setup["teacher"].id),
            },
            format="json",
        )
        response = client.post(
            "/api/v1/academics/class-teacher-assignments/unassign/",
            {"school_class": str(ct_setup["class"].id)},
            format="json",
        )
        assert response.status_code == 200, response.data
        ct_setup["class"].refresh_from_db()
        ct_setup["teacher"].refresh_from_db()
        assert ct_setup["class"].class_teacher_id is None
        assert ct_setup["teacher"].is_class_teacher is False
        assert not UserRoleAssignment.objects.filter(
            user=ct_setup["teacher_user"],
            role=UserRole.CLASS_TEACHER,
            is_active=True,
            source="class_assignment",
        ).exists()

    def test_list_includes_vacant_and_stream_rows(self, ct_setup):
        client = APIClient()
        client.force_authenticate(user=ct_setup["admin"])
        response = client.get("/api/v1/academics/class-teacher-assignments/")
        assert response.status_code == 200
        rows = response.data["data"]["results"]
        keys = {r["key"] for r in rows}
        assert f"class:{ct_setup['class'].id}" in keys
        assert f"stream:{ct_setup['stream'].id}" in keys

    def test_context_marks_is_class_teacher(self, ct_setup):
        from apps.academics.scoping import get_academic_context
        from apps.academics.services.class_teachers import assign_class_teacher

        assign_class_teacher(
            tenant=ct_setup["tenant"],
            actor=ct_setup["admin"],
            school_class_id=ct_setup["class"].id,
            teacher_id=ct_setup["teacher"].id,
        )
        ctx = get_academic_context(ct_setup["teacher_user"])
        assert ctx is not None
        assert ctx.is_class_teacher is True
        assert ct_setup["class"].id in ctx.class_teacher_class_ids
        assert ct_setup["class"].id in ctx.class_teacher_whole_class_ids
