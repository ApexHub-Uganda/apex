"""Class assignment marks — term-free flow under Academics → Assignments."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Subject, Term, Timetable
from apps.examinations.models import Exam, Grade, GradingScheme, GradingSchemeBand
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def assignment_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Assignment Marks Plan", slug="assignment-marks-plan", max_students=500)
    assign_plan_features(plan, [
        "classes", "subjects", "terms", "timetables", "marks_entry",
        "grade_calculation", "examination_management", "student_management", "academic_years",
    ])
    return plan


@pytest.fixture
def assignment_tenant(db, assignment_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Assignment School",
        code="ASGN",
        email="assign@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=assignment_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def assignment_teacher(db, assignment_tenant):
    from apps.core.constants import UserRole

    return onboard_staff(
        assignment_tenant,
        data={
            "first_name": "Class",
            "last_name": "Teacher",
            "email": "class.teacher@test.edu",
            "phone": "+254700000301",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def assignment_setup(db, assignment_tenant, assignment_teacher):
    year = AcademicYear.objects.create(
        tenant=assignment_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    Term.objects.create(
        tenant=assignment_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    assigned_class = Class.objects.create(
        tenant=assignment_tenant, name="Grade 5", code="G5", academic_year=year,
    )
    other_class = Class.objects.create(
        tenant=assignment_tenant, name="Grade 6", code="G6", academic_year=year,
    )
    assigned_subject = Subject.objects.create(
        tenant=assignment_tenant, name="Mathematics", code="MATH",
    )
    other_subject = Subject.objects.create(
        tenant=assignment_tenant, name="English", code="ENG",
    )
    teacher = assignment_teacher.teacher_profile
    Timetable.objects.create(
        tenant=assignment_tenant,
        school_class=assigned_class,
        subject=assigned_subject,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    student = Student.objects.create(
        tenant=assignment_tenant,
        admission_number="ASGN-001",
        first_name="Alex",
        last_name="Kimani",
        date_of_birth=date(2015, 5, 5),
        gender="male",
        school_class=assigned_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    scheme = GradingScheme.objects.create(tenant=assignment_tenant, name="Default", is_default=True)
    GradingSchemeBand.objects.create(
        tenant=assignment_tenant,
        scheme=scheme,
        grade="A",
        min_score=80,
        max_score=100,
        remarks="Excellent",
    )
    return {
        "assigned_class": assigned_class,
        "other_class": other_class,
        "assigned_subject": assigned_subject,
        "other_subject": other_subject,
        "teacher_user": assignment_teacher.user,
        "student": student,
        "scheme": scheme,
    }


@pytest.mark.django_db
class TestAssignmentMarks:
    def test_options_have_no_term_lock(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        response = api_client.get("/api/v1/academics/assignment-marks/options/")
        assert response.status_code == 200
        data = response.data["data"]
        assert data["scope_meta"]["term_locked"] is False
        assert data["scope_meta"]["is_assignment_flow"] is True
        assert "terms" not in data or data.get("terms", []) == []

    def test_teacher_creates_assignment_by_name(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        response = api_client.post(
            "/api/v1/academics/assignment-marks/create/",
            {
                "name": "Assignment 1",
                "subject": str(assignment_setup["assigned_subject"].id),
                "school_class": str(assignment_setup["assigned_class"].id),
            },
            format="json",
        )
        assert response.status_code == 200
        exam = Exam.objects.get(pk=response.data["data"]["id"])
        assert exam.name == "Assignment 1"
        assert exam.exam_type == "assignment"
        assert exam.term_id is None

    def test_teacher_cannot_create_for_unassigned_class(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        response = api_client.post(
            "/api/v1/academics/assignment-marks/create/",
            {
                "name": "Assignment 1",
                "subject": str(assignment_setup["other_subject"].id),
                "school_class": str(assignment_setup["other_class"].id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_teacher_saves_marks_without_term(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        create_resp = api_client.post(
            "/api/v1/academics/assignment-marks/create/",
            {
                "name": "Assignment 2",
                "subject": str(assignment_setup["assigned_subject"].id),
                "school_class": str(assignment_setup["assigned_class"].id),
            },
            format="json",
        )
        exam_id = create_resp.data["data"]["id"]
        save_resp = api_client.post(
            "/api/v1/academics/assignment-marks/bulk/",
            {
                "exam": exam_id,
                "entries": [
                    {
                        "student": str(assignment_setup["student"].id),
                        "score": "88",
                        "remarks": "Strong work",
                    },
                ],
            },
            format="json",
        )
        assert save_resp.status_code == 200
        grade = Grade.objects.get(exam_id=exam_id, student=assignment_setup["student"])
        assert str(grade.score) == "88.00"
        assert grade.grade == ""

    def test_grade_calculation_applies_to_assignment(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        exam = Exam.objects.create(
            tenant=assignment_setup["teacher_user"].tenant,
            name="Assignment 3",
            subject=assignment_setup["assigned_subject"],
            school_class=assignment_setup["assigned_class"],
            term=None,
            exam_date=date.today(),
            max_score=100,
            exam_type="assignment",
            lifecycle_status="published",
        )
        Grade.objects.create(
            tenant=assignment_setup["teacher_user"].tenant,
            exam=exam,
            student=assignment_setup["student"],
            score=88,
            grade="",
        )
        response = api_client.post(
            "/api/v1/academics/assignment-grades/apply/",
            {
                "scheme": str(assignment_setup["scheme"].id),
                "exam": str(exam.id),
            },
            format="json",
        )
        assert response.status_code == 200
        grade = Grade.objects.get(exam=exam, student=assignment_setup["student"])
        assert grade.grade == "A"

    def test_examination_marks_entry_still_term_locked(self, api_client, assignment_setup):
        api_client.force_authenticate(user=assignment_setup["teacher_user"])
        response = api_client.get("/api/v1/examinations/marks-entry/options/")
        assert response.status_code == 200
        assert response.data["data"]["scope_meta"]["term_locked"] is True