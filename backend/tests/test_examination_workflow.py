"""Marks approval and assessment lifecycle workflow tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Department, Subject, Term, Timetable
from apps.core.constants import UserRole
from apps.examinations.constants import (
    EXAM_LIFECYCLE_PUBLISHED,
    MARKS_STATUS_DRAFT,
    MARKS_STATUS_LOCKED,
    MARKS_STATUS_SUBMITTED,
)
from apps.examinations.models import Exam, Grade
from apps.examinations.services import bulk_upsert_grades
from apps.examinations.workflow import (
    MarksWorkflowError,
    approve_exam_marks,
    lock_exam_marks,
    publish_exam,
    reopen_exam_marks,
    submit_exam_marks,
)
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_permissions import save_role_permissions


@pytest.fixture
def workflow_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Workflow Plan", slug="workflow-plan", max_students=500)
    assign_plan_features(plan, [
        "examination_management", "assessment_management", "marks_entry", "marks_approval",
        "classes", "subjects", "terms",
    ])
    return plan


@pytest.fixture
def workflow_tenant(db, workflow_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Workflow School",
        code="FLOW",
        email="flow@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=workflow_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def workflow_teacher(db, workflow_tenant):
    return onboard_staff(
        workflow_tenant,
        data={
            "first_name": "Flow",
            "last_name": "Teacher",
            "email": "flow.teacher@test.edu",
            "phone": "+254700000301",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def workflow_hod(db, workflow_tenant):
    return onboard_staff(
        workflow_tenant,
        data={
            "first_name": "Flow",
            "last_name": "HoD",
            "email": "flow.hod@test.edu",
            "phone": "+254700000302",
            "portal_role": UserRole.HEAD_OF_DEPARTMENT,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def workflow_exam(db, workflow_tenant, workflow_teacher, workflow_hod):
    year = AcademicYear.objects.create(
        tenant=workflow_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=workflow_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=workflow_tenant, name="Grade 7", code="G7", academic_year=year,
    )
    department = Department.objects.create(
        tenant=workflow_tenant, name="Sciences", code="SCI-DEPT", head=workflow_hod,
    )
    subject = Subject.objects.create(
        tenant=workflow_tenant, name="Science", code="SCI", department=department,
    )
    workflow_hod.department = department
    workflow_hod.save(update_fields=["department"])
    teacher = workflow_teacher.teacher_profile
    teacher.subjects.add(subject)
    Timetable.objects.create(
        tenant=workflow_tenant,
        school_class=school_class,
        subject=subject,
        teacher=teacher,
        day_of_week=1,
        start_time="09:00",
        end_time="10:00",
    )
    student = Student.objects.create(
        tenant=workflow_tenant,
        admission_number="FLOW-001",
        first_name="Sam",
        last_name="Otieno",
        date_of_birth=date(2014, 4, 4),
        gender="male",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    exam = Exam.objects.create(
        tenant=workflow_tenant,
        name="Science Test",
        subject=subject,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 15),
        max_score=100,
        exam_type="midterm",
    )
    return {"exam": exam, "student": student, "teacher_user": workflow_teacher.user}


@pytest.mark.django_db
class TestExaminationWorkflow:
    def test_publish_then_submit_approve_lock_cycle(self, workflow_exam, workflow_hod):
        exam = workflow_exam["exam"]
        student = workflow_exam["student"]
        teacher_user = workflow_exam["teacher_user"]
        hod_user = workflow_hod.user

        publish_exam(exam=exam, user=teacher_user)
        exam.refresh_from_db()
        assert exam.lifecycle_status == EXAM_LIFECYCLE_PUBLISHED

        bulk_upsert_grades(
            tenant=exam.tenant,
            exam=exam,
            entries=[{"student": str(student.id), "score": "72"}],
            user=teacher_user,
        )
        submit_exam_marks(exam=exam, user=teacher_user)
        exam.refresh_from_db()
        assert exam.marks_status == MARKS_STATUS_SUBMITTED

        approve_exam_marks(exam=exam, user=hod_user)
        lock_exam_marks(exam=exam, user=hod_user)
        exam.refresh_from_db()
        assert exam.marks_status == MARKS_STATUS_LOCKED

        grade = Grade.objects.get(exam=exam, student=student)
        assert grade.entry_status == MARKS_STATUS_LOCKED

        with pytest.raises(MarksWorkflowError):
            bulk_upsert_grades(
                tenant=exam.tenant,
                exam=exam,
                entries=[{"student": str(student.id), "score": "80"}],
                user=teacher_user,
            )

    def test_reopen_resets_marks_to_draft(self, workflow_exam, workflow_hod):
        exam = workflow_exam["exam"]
        student = workflow_exam["student"]
        teacher_user = workflow_exam["teacher_user"]
        hod_user = workflow_hod.user

        publish_exam(exam=exam, user=teacher_user)
        bulk_upsert_grades(
            tenant=exam.tenant,
            exam=exam,
            entries=[{"student": str(student.id), "score": "65"}],
            user=teacher_user,
        )
        submit_exam_marks(exam=exam, user=teacher_user)
        approve_exam_marks(exam=exam, user=hod_user)
        lock_exam_marks(exam=exam, user=hod_user)

        save_role_permissions(exam.tenant, [{
            "role": UserRole.DIRECTOR_OF_STUDIES,
            "module_key": "examinations",
            "can_read": True,
            "can_write": True,
        }])
        from django.contrib.auth import get_user_model

        dos = get_user_model().objects.create_user(
            email="dos@test.edu",
            password="TestPass@2026",
            first_name="DoS",
            last_name="User",
            role=UserRole.DIRECTOR_OF_STUDIES,
            tenant=exam.tenant,
            is_email_verified=True,
        )

        reopen_exam_marks(exam=exam, user=dos, reason="Correction required")
        exam.refresh_from_db()
        assert exam.marks_status == MARKS_STATUS_DRAFT
        assert exam.marks_reopen_reason == "Correction required"

        bulk_upsert_grades(
            tenant=exam.tenant,
            exam=exam,
            entries=[{"student": str(student.id), "score": "70"}],
            user=teacher_user,
        )
        grade = Grade.objects.get(exam=exam, student=student)
        assert grade.score == Decimal("70")

    def test_submit_requires_grades(self, workflow_exam):
        exam = workflow_exam["exam"]
        publish_exam(exam=exam, user=workflow_exam["teacher_user"])
        with pytest.raises(MarksWorkflowError):
            submit_exam_marks(exam=exam, user=workflow_exam["teacher_user"])

    def test_workflow_api_endpoints(self, workflow_exam, workflow_hod):
        exam = workflow_exam["exam"]
        student = workflow_exam["student"]
        client = APIClient()
        client.force_authenticate(user=workflow_exam["teacher_user"])

        assert client.post(f"/api/v1/examinations/exams/{exam.id}/publish/").status_code == 200
        exam.refresh_from_db()
        bulk_upsert_grades(
            tenant=exam.tenant,
            exam=exam,
            entries=[{"student": str(student.id), "score": "55"}],
            user=workflow_exam["teacher_user"],
        )
        assert client.post(f"/api/v1/examinations/exams/{exam.id}/submit-marks/").status_code == 200

        hod_client = APIClient()
        hod_client.force_authenticate(user=workflow_hod.user)
        assert hod_client.post(f"/api/v1/examinations/exams/{exam.id}/approve-marks/").status_code == 200
        assert hod_client.post(f"/api/v1/examinations/exams/{exam.id}/lock-marks/").status_code == 200