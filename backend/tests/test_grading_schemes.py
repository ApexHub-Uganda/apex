"""Grading scheme and grade calculation tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Subject, Term, Timetable
from apps.examinations.models import Exam, Grade, GradingScheme, GradingSchemeBand
from apps.staff.services import onboard_staff
from apps.core.constants import UserRole
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def grading_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Grading Plan", slug="grading-plan", max_students=500)
    assign_plan_features(plan, [
        "grading", "grade_calculation", "marks_entry", "examination_management",
        "classes", "subjects", "terms", "subject_assignment",
    ])
    return plan


@pytest.fixture
def grading_tenant(db, grading_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Grading School",
        code="GRDSCH",
        email="grading@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=grading_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def dos_user(db, grading_tenant):
    staff = onboard_staff(
        grading_tenant,
        data={
            "first_name": "Grade",
            "last_name": "DOS",
            "email": "grade.dos@test.edu",
            "phone": "+254700000601",
            "portal_role": UserRole.DIRECTOR_OF_STUDIES,
            "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.fixture
def subject_teacher_user(db, grading_tenant):
    staff = onboard_staff(
        grading_tenant,
        data={
            "first_name": "Math",
            "last_name": "Teacher",
            "email": "math.teacher@grading.test",
            "phone": "+254700000602",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.fixture
def grading_setup(db, grading_tenant, dos_user, subject_teacher_user):
    year = AcademicYear.objects.create(
        tenant=grading_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=grading_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=grading_tenant, name="Grade 7", code="G7", academic_year=year,
    )
    math = Subject.objects.create(tenant=grading_tenant, name="Mathematics", code="MTC")
    teacher = subject_teacher_user.staff_profile.teacher_profile
    Timetable.objects.create(
        tenant=grading_tenant,
        school_class=school_class,
        subject=math,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    exam = Exam.objects.create(
        tenant=grading_tenant,
        name="Midterm Maths",
        subject=math,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 1),
        max_score=Decimal("100"),
        lifecycle_status="published",
    )
    student = Student.objects.create(
        tenant=grading_tenant,
        first_name="Jane",
        last_name="Learner",
        admission_number="G7-001",
        date_of_birth=date(2012, 5, 15),
        gender="female",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    Grade.objects.create(
        tenant=grading_tenant,
        exam=exam,
        student=student,
        score=Decimal("85"),
        grade="",
    )
    return {
        "year": year,
        "term": term,
        "class": school_class,
        "subject": math,
        "exam": exam,
        "student": student,
        "teacher_user": subject_teacher_user,
    }


@pytest.mark.django_db
class TestGradingSchemes:
    def test_sync_scheme_creates_bands(self, api_client, dos_user, grading_setup):
        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/examinations/grading-schemes/sync/",
            {
                "name": "O-Level",
                "description": "Standard scale",
                "is_default": True,
                "bands": [
                    {"min_score": 80, "max_score": 100, "grade": "A", "remarks": "Excellent"},
                    {"min_score": 70, "max_score": 79, "grade": "B", "remarks": "Good"},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["name"] == "O-Level"
        assert GradingSchemeBand.objects.filter(scheme__name="O-Level").count() == 2

    def test_apply_scheme_to_entered_marks(self, api_client, grading_setup, grading_tenant):
        """Only the subject teacher may apply a grading scheme to their marks."""
        scheme = GradingScheme.objects.create(
            tenant=grading_tenant, name="Test Scale", is_default=True,
        )
        GradingSchemeBand.objects.create(
            tenant=grading_tenant, scheme=scheme,
            min_score=Decimal("80"), max_score=Decimal("100"), grade="A",
        )
        GradingSchemeBand.objects.create(
            tenant=grading_tenant, scheme=scheme,
            min_score=Decimal("70"), max_score=Decimal("79"), grade="B",
        )

        api_client.force_authenticate(user=grading_setup["teacher_user"])
        response = api_client.post(
            "/api/v1/examinations/grade-calculation/apply/",
            {"scheme": str(scheme.id), "exam": str(grading_setup["exam"].id)},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["updated_count"] == 1
        assert response.data["data"]["rows"][0]["grade"] == "A"

        grade = Grade.objects.get(exam=grading_setup["exam"], student=grading_setup["student"])
        assert grade.grade == "A"

    def test_dos_cannot_apply_scheme(self, api_client, dos_user, grading_setup, grading_tenant):
        scheme = GradingScheme.objects.create(
            tenant=grading_tenant, name="Blocked Scale", is_default=True,
        )
        GradingSchemeBand.objects.create(
            tenant=grading_tenant, scheme=scheme,
            min_score=Decimal("80"), max_score=Decimal("100"), grade="A",
        )
        api_client.force_authenticate(user=dos_user)
        response = api_client.post(
            "/api/v1/examinations/grade-calculation/apply/",
            {"scheme": str(scheme.id), "exam": str(grading_setup["exam"].id)},
            format="json",
        )
        assert response.status_code == 403

    def test_grade_calculation_options_lists_schemes(self, api_client, dos_user, grading_tenant):
        GradingScheme.objects.create(tenant=grading_tenant, name="CBC", is_default=True)
        api_client.force_authenticate(user=dos_user)
        response = api_client.get("/api/v1/examinations/grade-calculation/options/")
        assert response.status_code == 200
        schemes = response.data["data"]["schemes"]
        assert any(s["label"] == "CBC" for s in schemes)