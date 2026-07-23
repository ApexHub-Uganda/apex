"""Academic data scoping by teaching assignments."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Subject, Term, Timetable
from apps.academics.scoping import (
    filter_queryset_for_user,
    get_academic_context,
    user_can_access_exam,
)
from apps.core.constants import UserRole
from apps.examinations.models import Exam
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features
from apps.students.models import Student


@pytest.fixture
def scoping_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Scoping Plan", slug="scoping-plan", max_students=500)
    assign_plan_features(plan, [
        "classes", "subjects", "terms", "timetables", "marks_entry",
        "examination_management", "student_management", "academic_years",
    ])
    return plan


@pytest.fixture
def scoping_tenant(db, scoping_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Scoping School",
        code="SCOPE",
        email="scope@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=scoping_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def assigned_teacher(db, scoping_tenant):
    return onboard_staff(
        scoping_tenant,
        data={
            "first_name": "Assigned",
            "last_name": "Teacher",
            "email": "assigned.teacher@test.edu",
            "phone": "+254700000201",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def academic_setup(db, scoping_tenant, assigned_teacher):
    year = AcademicYear.objects.create(
        tenant=scoping_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=scoping_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    assigned_class = Class.objects.create(
        tenant=scoping_tenant, name="Grade 5", code="G5", academic_year=year,
    )
    other_class = Class.objects.create(
        tenant=scoping_tenant, name="Grade 6", code="G6", academic_year=year,
    )
    assigned_subject = Subject.objects.create(
        tenant=scoping_tenant, name="Mathematics", code="MATH",
    )
    other_subject = Subject.objects.create(
        tenant=scoping_tenant, name="English", code="ENG",
    )
    teacher = assigned_teacher.teacher_profile
    Timetable.objects.create(
        tenant=scoping_tenant,
        school_class=assigned_class,
        subject=assigned_subject,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    assigned_exam = Exam.objects.create(
        tenant=scoping_tenant,
        name="Math Midterm",
        subject=assigned_subject,
        school_class=assigned_class,
        term=term,
        exam_date=date(2026, 3, 1),
        max_score=100,
        exam_type="midterm",
        lifecycle_status="published",
    )
    other_exam = Exam.objects.create(
        tenant=scoping_tenant,
        name="English Midterm",
        subject=other_subject,
        school_class=other_class,
        term=term,
        exam_date=date(2026, 3, 1),
        max_score=100,
        exam_type="midterm",
    )
    Student.objects.create(
        tenant=scoping_tenant,
        admission_number="SCOPE-001",
        first_name="Alex",
        last_name="Kimani",
        date_of_birth=date(2015, 5, 5),
        gender="male",
        school_class=assigned_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    return {
        "year": year,
        "term": term,
        "assigned_class": assigned_class,
        "other_class": other_class,
        "assigned_subject": assigned_subject,
        "other_subject": other_subject,
        "assigned_exam": assigned_exam,
        "other_exam": other_exam,
        "teacher_user": assigned_teacher.user,
    }


@pytest.mark.django_db
class TestAcademicScoping:
    def test_teacher_context_from_timetable(self, scoping_tenant, academic_setup):
        ctx = get_academic_context(academic_setup["teacher_user"])
        assert ctx is not None
        assert ctx.teacher is not None
        assert academic_setup["assigned_subject"].id in ctx.assigned_subject_ids
        assert academic_setup["assigned_class"].id in ctx.assigned_class_ids
        assert academic_setup["other_class"].id not in ctx.assigned_class_ids

    def test_filter_subjects_and_classes(self, scoping_tenant, academic_setup):
        user = academic_setup["teacher_user"]
        subjects = filter_queryset_for_user(Subject.objects.filter(tenant=scoping_tenant), user)
        assert set(subjects.values_list("id", flat=True)) == {academic_setup["assigned_subject"].id}

        classes = filter_queryset_for_user(Class.objects.filter(tenant=scoping_tenant), user)
        assert set(classes.values_list("id", flat=True)) == {academic_setup["assigned_class"].id}

    def test_filter_exams(self, scoping_tenant, academic_setup):
        user = academic_setup["teacher_user"]
        exams = filter_queryset_for_user(Exam.objects.filter(tenant=scoping_tenant), user)
        assert set(exams.values_list("id", flat=True)) == {academic_setup["assigned_exam"].id}

    def test_user_can_access_exam(self, academic_setup):
        user = academic_setup["teacher_user"]
        assert user_can_access_exam(user, academic_setup["assigned_exam"]) is True
        assert user_can_access_exam(user, academic_setup["other_exam"]) is False

    def test_classes_api_scoped_for_teacher(self, api_client, academic_setup):
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.get("/api/v1/academics/classes/")
        assert response.status_code == 200
        results = response.data.get("results") or response.data.get("data", {}).get("results", [])
        ids = {row["id"] for row in results}
        assert ids == {str(academic_setup["assigned_class"].id)}

    def test_marks_entry_options_scoped_for_teacher(self, api_client, academic_setup):
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.get("/api/v1/examinations/marks-entry/options/")
        assert response.status_code == 200
        data = response.data["data"]
        subject_ids = {s["value"] for s in data["subjects"]}
        assert subject_ids == {str(academic_setup["assigned_subject"].id)}
        assert data["scope_meta"]["term_locked"] is True
        assert data["scope_meta"]["is_unrestricted"] is False

        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {"subject": academic_setup["other_subject"].id},
        )
        assert response.status_code == 200
        assert response.data["data"]["classes"] == []

    def test_marks_entry_terms_locked_to_current_for_teacher(self, api_client, academic_setup, scoping_tenant):
        year = academic_setup["year"]
        Term.objects.create(
            tenant=scoping_tenant,
            academic_year=year,
            name="Term 2",
            term_number=2,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 1),
            is_current=False,
        )
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": academic_setup["assigned_subject"].id,
                "school_class": academic_setup["assigned_class"].id,
            },
        )
        assert response.status_code == 200
        terms = response.data["data"]["terms"]
        assert len(terms) == 1
        assert terms[0]["value"] == str(academic_setup["term"].id)

    def test_marks_entry_ignores_client_past_term_and_uses_current(
        self, api_client, academic_setup, scoping_tenant,
    ):
        """Teachers cannot pick a past term — server always uses the current term."""
        past_term = Term.objects.create(
            tenant=scoping_tenant,
            academic_year=academic_setup["year"],
            name="Past Term",
            term_number=3,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 1),
            is_current=False,
        )
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": academic_setup["assigned_subject"].id,
                "school_class": academic_setup["assigned_class"].id,
                "term": past_term.id,
            },
        )
        assert response.status_code == 200
        data = response.data["data"]
        assert data["scope_meta"]["current_term_id"] == str(academic_setup["term"].id)
        assert data["auto_select"]["term"] == str(academic_setup["term"].id)
        # Assigned exam in the current term is still listed
        exam_ids = {e["value"] for e in data["exams"]}
        assert str(academic_setup["assigned_exam"].id) in exam_ids

    def test_marks_entry_bulk_denied_for_unassigned_exam(self, api_client, academic_setup):
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {"exam": str(academic_setup["other_exam"].id)},
            format="json",
        )
        assert response.status_code == 403

    def test_teacher_sees_only_active_term(self, api_client, academic_setup, scoping_tenant):
        year = academic_setup["year"]
        Term.objects.create(
            tenant=scoping_tenant,
            academic_year=year,
            name="Term 2",
            term_number=2,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 1),
            is_current=False,
        )
        api_client.force_authenticate(user=academic_setup["teacher_user"])
        response = api_client.get("/api/v1/academics/terms/")
        assert response.status_code == 200
        results = response.data.get("results") or response.data.get("data", {}).get("results", [])
        assert len(results) == 1
        assert results[0]["name"] == "Term 1"

    def test_filter_students_for_teacher(self, scoping_tenant, academic_setup):
        user = academic_setup["teacher_user"]
        students = filter_queryset_for_user(Student.objects.filter(tenant=scoping_tenant), user)
        assert students.count() == 1
        assert students.first().admission_number == "SCOPE-001"