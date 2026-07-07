"""Phase 3–5 workflow API tests: workspace, approval queue, bulk actions, attendance."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, ClassNotice, Department, Subject, Term, Timetable
from apps.core.constants import UserRole
from apps.examinations.constants import MARKS_STATUS_LOCKED, MARKS_STATUS_SUBMITTED
from apps.examinations.models import Exam
from apps.examinations.services import bulk_upsert_grades
from apps.examinations.workflow import (
    approve_exam_marks,
    lock_exam_marks,
    publish_exam,
    submit_exam_marks,
)
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def workflow_api_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Workflow API Plan", slug="workflow-api-plan", max_students=500)
    assign_plan_features(plan, [
        "teacher_workspace", "hod_workspace", "dos_workspace", "class_teacher_tools",
        "examination_management", "assessment_management", "marks_entry", "marks_approval",
        "lesson_attendance", "class_notices", "discipline_remarks",
        "classes", "subjects", "terms", "student_management",
    ])
    return plan


@pytest.fixture
def workflow_api_tenant(db, workflow_api_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Workflow API School",
        code="WAPI",
        email="wapi@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=workflow_api_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def api_teacher(db, workflow_api_tenant):
    return onboard_staff(
        workflow_api_tenant,
        data={
            "first_name": "API",
            "last_name": "Teacher",
            "email": "api.teacher@test.edu",
            "phone": "+254700000401",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def api_hod(db, workflow_api_tenant):
    return onboard_staff(
        workflow_api_tenant,
        data={
            "first_name": "API",
            "last_name": "HoD",
            "email": "api.hod@test.edu",
            "phone": "+254700000402",
            "portal_role": UserRole.HEAD_OF_DEPARTMENT,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def api_dos(db, workflow_api_tenant):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="api.dos@test.edu",
        password="TestPass@2026",
        first_name="API",
        last_name="DoS",
        role=UserRole.DIRECTOR_OF_STUDIES,
        tenant=workflow_api_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def api_setup(db, workflow_api_tenant, api_teacher, api_hod):
    year = AcademicYear.objects.create(
        tenant=workflow_api_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=workflow_api_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=workflow_api_tenant, name="Grade 8", code="G8", academic_year=year,
    )
    other_class = Class.objects.create(
        tenant=workflow_api_tenant, name="Grade 9", code="G9", academic_year=year,
    )
    department = Department.objects.create(
        tenant=workflow_api_tenant, name="Languages", code="LANG", head=api_hod,
    )
    subject = Subject.objects.create(
        tenant=workflow_api_tenant, name="English", code="ENG", department=department,
    )
    other_subject = Subject.objects.create(
        tenant=workflow_api_tenant, name="History", code="HIST",
    )
    api_hod.department = department
    api_hod.save(update_fields=["department"])
    teacher = api_teacher.teacher_profile
    teacher.subjects.add(subject)
    Timetable.objects.create(
        tenant=workflow_api_tenant,
        school_class=school_class,
        subject=subject,
        teacher=teacher,
        day_of_week=2,
        start_time="10:00",
        end_time="11:00",
    )
    student = Student.objects.create(
        tenant=workflow_api_tenant,
        admission_number="WAPI-001",
        first_name="Jane",
        last_name="Wanjiku",
        date_of_birth=date(2013, 6, 6),
        gender="female",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    draft_exam = Exam.objects.create(
        tenant=workflow_api_tenant,
        name="English Draft",
        subject=subject,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 20),
        max_score=100,
        exam_type="midterm",
        lifecycle_status="draft",
    )
    published_exam = Exam.objects.create(
        tenant=workflow_api_tenant,
        name="English Test",
        subject=subject,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 21),
        max_score=100,
        exam_type="midterm",
        lifecycle_status="published",
    )
    other_exam = Exam.objects.create(
        tenant=workflow_api_tenant,
        name="History Test",
        subject=other_subject,
        school_class=other_class,
        term=term,
        exam_date=date(2026, 3, 22),
        max_score=100,
        exam_type="midterm",
        lifecycle_status="published",
    )
    return {
        "year": year,
        "term": term,
        "school_class": school_class,
        "other_class": other_class,
        "subject": subject,
        "student": student,
        "draft_exam": draft_exam,
        "published_exam": published_exam,
        "other_exam": other_exam,
        "teacher_user": api_teacher.user,
        "hod_user": api_hod.user,
    }


def _prepare_submitted_exam(api_setup):
    exam = api_setup["published_exam"]
    teacher_user = api_setup["teacher_user"]
    student = api_setup["student"]
    publish_exam(exam=exam, user=teacher_user)
    bulk_upsert_grades(
        tenant=exam.tenant,
        exam=exam,
        entries=[{"student": str(student.id), "score": "78"}],
        user=teacher_user,
    )
    submit_exam_marks(exam=exam, user=teacher_user)
    exam.refresh_from_db()
    return exam


@pytest.mark.django_db
class TestAcademicWorkspaceAPI:
    def test_teacher_workspace_returns_scoped_counts(self, api_setup):
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.get("/api/v1/academics/workspace/")
        assert response.status_code == 200
        data = response.data["data"]
        assert data["role"] == UserRole.TEACHER
        assert "draft_marks" in data["counts"]
        assert "assigned_classes" in data["counts"]
        assert data["counts"]["assigned_classes"] == 1
        quick_paths = {link["path"] for link in data["quick_links"]}
        assert "/school-admin/examinations/marks" in quick_paths

    def test_hod_workspace_includes_approval_queue(self, api_setup):
        _prepare_submitted_exam(api_setup)
        client = APIClient()
        client.force_authenticate(user=api_setup["hod_user"])
        response = client.get("/api/v1/academics/workspace/")
        assert response.status_code == 200
        data = response.data["data"]
        assert data["role"] == UserRole.HEAD_OF_DEPARTMENT
        assert data["counts"]["pending_approval"] >= 1
        assert len(data["queues"]["marks_approval"]) >= 1


@pytest.mark.django_db
class TestMarksApprovalQueueAPI:
    def test_queue_lists_submitted_exams_scoped_to_hod(self, api_setup):
        exam = _prepare_submitted_exam(api_setup)
        client = APIClient()
        client.force_authenticate(user=api_setup["hod_user"])
        response = client.get("/api/v1/examinations/marks-approval/queue/")
        assert response.status_code == 200
        results = response.data["data"]["results"]
        ids = {row["id"] for row in results}
        assert str(exam.id) in ids

    def test_teacher_cannot_access_approval_queue(self, api_setup):
        _prepare_submitted_exam(api_setup)
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.get("/api/v1/examinations/marks-approval/queue/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestWorkflowBulkAPI:
    def test_hod_bulk_approve(self, api_setup):
        exam = _prepare_submitted_exam(api_setup)
        client = APIClient()
        client.force_authenticate(user=api_setup["hod_user"])
        response = client.post(
            "/api/v1/examinations/workflow/bulk/",
            {"action": "approve", "exam_ids": [str(exam.id)]},
            format="json",
        )
        assert response.status_code == 200
        exam.refresh_from_db()
        assert exam.marks_status == "approved"
        assert str(exam.id) in response.data["data"]["processed"]

    def test_dos_bulk_publish_draft_assessments(self, api_setup, api_dos):
        draft = api_setup["draft_exam"]
        client = APIClient()
        client.force_authenticate(user=api_dos)
        response = client.post(
            "/api/v1/examinations/workflow/bulk/",
            {"action": "publish", "exam_ids": [str(draft.id)]},
            format="json",
        )
        assert response.status_code == 200
        draft.refresh_from_db()
        assert draft.lifecycle_status == "published"

    def test_hod_cannot_bulk_publish_draft_assessments(self, api_setup):
        draft = api_setup["draft_exam"]
        client = APIClient()
        client.force_authenticate(user=api_setup["hod_user"])
        response = client.post(
            "/api/v1/examinations/workflow/bulk/",
            {"action": "publish", "exam_ids": [str(draft.id)]},
            format="json",
        )
        assert response.status_code == 403

    def test_teacher_cannot_bulk_approve(self, api_setup):
        exam = _prepare_submitted_exam(api_setup)
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.post(
            "/api/v1/examinations/workflow/bulk/",
            {"action": "approve", "exam_ids": [str(exam.id)]},
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestReopenMarksAPI:
    def test_hod_cannot_reopen_locked_marks(self, api_setup, api_dos):
        exam = _prepare_submitted_exam(api_setup)
        approve_exam_marks(exam=exam, user=api_setup["hod_user"])
        lock_exam_marks(exam=exam, user=api_setup["hod_user"])
        exam.refresh_from_db()
        assert exam.marks_status == MARKS_STATUS_LOCKED

        hod_client = APIClient()
        hod_client.force_authenticate(user=api_setup["hod_user"])
        response = hod_client.post(
            f"/api/v1/examinations/exams/{exam.id}/reopen-marks/",
            {"reason": "Should fail"},
            format="json",
        )
        assert response.status_code == 403
        assert response.data.get("code") == "forbidden_reopen"

        dos_client = APIClient()
        dos_client.force_authenticate(user=api_dos)
        response = dos_client.post(
            f"/api/v1/examinations/exams/{exam.id}/reopen-marks/",
            {"reason": "Correction required"},
            format="json",
        )
        assert response.status_code == 200
        exam.refresh_from_db()
        assert exam.marks_status == "draft"


@pytest.mark.django_db
class TestClassNoticePublishAPI:
    def test_publish_class_notice(self, api_setup):
        school_class = api_setup["school_class"]
        teacher = api_setup["teacher_user"].staff_profile.teacher_profile
        school_class.class_teacher = teacher
        school_class.save(update_fields=["class_teacher"])

        notice = ClassNotice.objects.create(
            tenant=api_setup["published_exam"].tenant,
            school_class=school_class,
            author=teacher,
            title="Parent meeting",
            body="Friday at 3pm.",
            is_published=False,
            created_by=api_setup["teacher_user"],
            updated_by=api_setup["teacher_user"],
        )
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.post(f"/api/v1/academics/class-notices/{notice.id}/publish/")
        assert response.status_code == 200
        notice.refresh_from_db()
        assert notice.is_published is True
        assert notice.published_at is not None


@pytest.mark.django_db
class TestLessonAttendanceBulkAPI:
    def test_bulk_save_lesson_attendance(self, api_setup):
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.post(
            "/api/v1/attendance/lesson-sessions/bulk/",
            {
                "school_class": str(api_setup["school_class"].id),
                "subject": str(api_setup["subject"].id),
                "date": "2026-03-15",
                "entries": [
                    {"student": str(api_setup["student"].id), "status": "present"},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["saved"] == 1

    def test_teacher_cannot_mark_other_class(self, api_setup):
        client = APIClient()
        client.force_authenticate(user=api_setup["teacher_user"])
        response = client.post(
            "/api/v1/attendance/lesson-sessions/bulk/",
            {
                "school_class": str(api_setup["other_class"].id),
                "subject": str(api_setup["subject"].id),
                "date": "2026-03-15",
                "entries": [],
            },
            format="json",
        )
        assert response.status_code == 403