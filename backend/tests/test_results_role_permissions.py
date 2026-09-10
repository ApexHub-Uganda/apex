"""Examination results role boundaries: subject teacher, class teacher, DoS."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Subject, Term, Timetable
from apps.academics.scoping import (
    results_role_capabilities,
    user_can_edit_class_teacher_remarks,
    user_can_print_report_cards,
    user_can_write_exam_marks,
    user_is_subject_marks_teacher,
)
from apps.core.constants import UserRole
from apps.examinations.models import Exam, Grade, ReportCard
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def results_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Results Plan", slug="results-role-plan", max_students=500)
    assign_plan_features(plan, [
        "classes", "subjects", "terms", "timetables", "marks_entry", "grade_calculation",
        "examination_management", "student_management", "academic_years",
        "result_processing", "report_cards", "class_report_cards", "marks_approval",
        "dos_workspace", "class_teacher_tools",
    ])
    return plan


@pytest.fixture
def results_tenant(db, results_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Results Role School",
        code="RRS",
        email="results@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=results_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def results_setup(db, results_tenant):
    year = AcademicYear.objects.create(
        tenant=results_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=results_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=results_tenant, name="S.1", code="S1", academic_year=year,
    )
    other_class = Class.objects.create(
        tenant=results_tenant, name="S.2", code="S2", academic_year=year,
    )
    math = Subject.objects.create(tenant=results_tenant, name="Mathematics", code="MATH")
    eng = Subject.objects.create(tenant=results_tenant, name="English", code="ENG")

    subject_staff = onboard_staff(
        results_tenant,
        data={
            "first_name": "Math",
            "last_name": "Teacher",
            "email": "math.teacher@rrs.test",
            "phone": "+256700000101",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    class_staff = onboard_staff(
        results_tenant,
        data={
            "first_name": "Class",
            "last_name": "Teacher",
            "email": "class.teacher@rrs.test",
            "phone": "+256700000102",
            "portal_role": UserRole.CLASS_TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    dos_staff = onboard_staff(
        results_tenant,
        data={
            "first_name": "Director",
            "last_name": "Studies",
            "email": "dos@rrs.test",
            "phone": "+256700000103",
            "portal_role": UserRole.DIRECTOR_OF_STUDIES,
            "date_joined": "2026-01-01",
        },
    )

    math_teacher = subject_staff.teacher_profile
    class_teacher = class_staff.teacher_profile
    school_class.class_teacher = class_teacher
    school_class.save(update_fields=["class_teacher"])

    Timetable.objects.create(
        tenant=results_tenant,
        school_class=school_class,
        subject=math,
        teacher=math_teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    # Class teacher also teaches English in their class (subject-teacher dual role)
    Timetable.objects.create(
        tenant=results_tenant,
        school_class=school_class,
        subject=eng,
        teacher=class_teacher,
        day_of_week=1,
        start_time="09:00",
        end_time="10:00",
    )

    math_exam = Exam.objects.create(
        tenant=results_tenant,
        name="Math CAT",
        subject=math,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 1),
        max_score=100,
        exam_type="cat",
        lifecycle_status="published",
        marks_status="draft",
    )
    eng_exam = Exam.objects.create(
        tenant=results_tenant,
        name="English CAT",
        subject=eng,
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 2),
        max_score=100,
        exam_type="cat",
        lifecycle_status="published",
        marks_status="draft",
    )
    other_exam = Exam.objects.create(
        tenant=results_tenant,
        name="Math S2",
        subject=math,
        school_class=other_class,
        term=term,
        exam_date=date(2026, 3, 3),
        max_score=100,
        exam_type="cat",
        lifecycle_status="published",
    )

    student = Student.objects.create(
        tenant=results_tenant,
        admission_number="RRS-001",
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(2014, 1, 1),
        gender="female",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    Grade.objects.create(
        tenant=results_tenant,
        exam=math_exam,
        student=student,
        score=75,
        grade="B",
        remarks="Good",
    )
    Grade.objects.create(
        tenant=results_tenant,
        exam=eng_exam,
        student=student,
        score=82,
        grade="A",
        remarks="Excellent",
    )
    ReportCard.objects.create(
        tenant=results_tenant,
        student=student,
        term=term,
        school_class=school_class,
        average_score=78.5,
        rank=1,
        is_latest=True,
        is_published=False,
        teacher_remarks="",
    )

    return {
        "tenant": results_tenant,
        "term": term,
        "school_class": school_class,
        "other_class": other_class,
        "math": math,
        "eng": eng,
        "math_exam": math_exam,
        "eng_exam": eng_exam,
        "other_exam": other_exam,
        "student": student,
        "subject_teacher_user": subject_staff.user,
        "class_teacher_user": class_staff.user,
        "dos_user": dos_staff.user,
    }


@pytest.mark.django_db
class TestResultsRoleCapabilities:
    def test_subject_teacher_capabilities(self, results_setup):
        caps = results_role_capabilities(results_setup["subject_teacher_user"])
        assert caps["can_enter_marks"] is True
        assert caps["can_apply_grading"] is True
        assert caps["can_print_report_cards"] is False
        assert caps["can_edit_class_teacher_remarks"] is False
        assert caps["can_read_all_classes"] is False

    def test_class_teacher_capabilities(self, results_setup):
        caps = results_role_capabilities(results_setup["class_teacher_user"])
        assert caps["is_class_teacher"] is True
        assert caps["can_print_report_cards"] is True
        assert caps["can_edit_class_teacher_remarks"] is True
        assert str(results_setup["school_class"].id) in caps["headed_class_ids"]
        # Dual role: also teaches English
        assert caps["can_enter_marks"] is True

    def test_dos_capabilities(self, results_setup):
        caps = results_role_capabilities(results_setup["dos_user"])
        assert caps["is_dos"] is True
        assert caps["can_enter_marks"] is False
        assert caps["can_apply_grading"] is False
        assert caps["can_print_report_cards"] is True
        assert caps["can_read_all_classes"] is True
        assert caps["can_edit_class_teacher_remarks"] is False


@pytest.mark.django_db
class TestMarksWriteBoundaries:
    def test_only_subject_teacher_writes_own_exam(self, results_setup):
        math_exam = results_setup["math_exam"]
        eng_exam = results_setup["eng_exam"]
        other_exam = results_setup["other_exam"]

        st = results_setup["subject_teacher_user"]
        ct = results_setup["class_teacher_user"]
        dos = results_setup["dos_user"]

        assert user_can_write_exam_marks(st, math_exam) is True
        assert user_can_write_exam_marks(st, eng_exam) is False
        assert user_can_write_exam_marks(st, other_exam) is False

        assert user_can_write_exam_marks(ct, eng_exam) is True
        assert user_can_write_exam_marks(ct, math_exam) is False

        assert user_can_write_exam_marks(dos, math_exam) is False
        assert user_can_write_exam_marks(dos, eng_exam) is False
        assert user_is_subject_marks_teacher(dos) is False

    def test_bulk_marks_denied_for_dos(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["dos_user"])
        response = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {
                "exam": str(results_setup["math_exam"].id),
                "entries": [{"student": str(results_setup["student"].id), "score": 50}],
            },
            format="json",
        )
        assert response.status_code == 403

    def test_bulk_marks_denied_for_other_subject(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["subject_teacher_user"])
        response = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {
                "exam": str(results_setup["eng_exam"].id),
                "entries": [{"student": str(results_setup["student"].id), "score": 50}],
            },
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestReportCardPrintAndRemarks:
    def test_print_permission(self, results_setup):
        cid = results_setup["school_class"].id
        other = results_setup["other_class"].id
        st = results_setup["subject_teacher_user"]
        ct = results_setup["class_teacher_user"]
        dos = results_setup["dos_user"]

        assert user_can_print_report_cards(st, cid) is False
        assert user_can_print_report_cards(ct, cid) is True
        assert user_can_print_report_cards(ct, other) is False
        assert user_can_print_report_cards(dos, cid) is True
        assert user_can_print_report_cards(dos, other) is True

    def test_class_teacher_remarks_only_for_headed(self, results_setup):
        cid = results_setup["school_class"].id
        other = results_setup["other_class"].id
        assert user_can_edit_class_teacher_remarks(results_setup["class_teacher_user"], cid) is True
        assert user_can_edit_class_teacher_remarks(results_setup["class_teacher_user"], other) is False
        assert user_can_edit_class_teacher_remarks(results_setup["dos_user"], cid) is False
        assert user_can_edit_class_teacher_remarks(results_setup["subject_teacher_user"], cid) is False

    def test_subject_teacher_cannot_generate_report_cards(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["subject_teacher_user"])
        response = api_client.post(
            "/api/v1/academics/report-cards/generate/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_class_teacher_remarks_api(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["class_teacher_user"])
        response = api_client.post(
            "/api/v1/academics/report-cards/class-teacher-remarks/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
                "remarks": {str(results_setup["student"].id): "Keep it up!"},
            },
            format="json",
        )
        assert response.status_code == 200
        rc = ReportCard.objects.get(
            tenant=results_setup["tenant"],
            student=results_setup["student"],
            is_latest=True,
        )
        assert rc.teacher_remarks == "Keep it up!"

    def test_dos_cannot_set_class_teacher_remarks(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["dos_user"])
        response = api_client.post(
            "/api/v1/academics/report-cards/class-teacher-remarks/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
                "remarks": {str(results_setup["student"].id): "DoS note"},
            },
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestClassResultsOverview:
    def test_class_teacher_sees_all_subjects(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["class_teacher_user"])
        response = api_client.get(
            "/api/v1/academics/results/class-overview/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
            },
        )
        assert response.status_code == 200
        data = response.data["data"]
        subject_codes = {s["code"] for s in data["subjects"]}
        assert "MATH" in subject_codes
        assert "ENG" in subject_codes
        assert data["read_only"] is True
        assert data["student_count"] == 1
        # Results Processing exposes publish pipeline (draft vs report cards)
        pipe = data.get("report_pipeline") or {}
        assert "status" in pipe
        assert "can_generate" in pipe
        assert "can_publish" in pipe
        assert pipe.get("is_results_only") is True or pipe.get("status") in (
            "none", "draft", "partial", "published",
        )

    def test_subject_teacher_sees_own_subject_even_when_draft(self, api_client, results_setup):
        """Own subjects visible at any marks_status; unapproved other subjects hidden."""
        api_client.force_authenticate(user=results_setup["subject_teacher_user"])
        response = api_client.get(
            "/api/v1/academics/results/class-overview/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
            },
        )
        assert response.status_code == 200
        data = response.data["data"]
        codes = {s["code"] for s in data["subjects"]}
        assert codes == {"MATH"}
        assert data["visibility"]["approved_only_for_other_subjects"] is True
        # Subject totals + average columns present
        student = data["students"][0]
        assert "subject_totals" in student
        assert "average" in student
        math_id = next(s["id"] for s in data["subjects"] if s["code"] == "MATH")
        assert student["subject_totals"][math_id]["score"] is not None

    def test_subject_teacher_sees_other_subjects_when_approved(self, api_client, results_setup):
        eng_exam = results_setup["eng_exam"]
        eng_exam.marks_status = "approved"
        eng_exam.save(update_fields=["marks_status"])

        api_client.force_authenticate(user=results_setup["subject_teacher_user"])
        response = api_client.get(
            "/api/v1/academics/results/class-overview/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
            },
        )
        assert response.status_code == 200
        codes = {s["code"] for s in response.data["data"]["subjects"]}
        assert "MATH" in codes
        assert "ENG" in codes
        # Can edit only own subject
        by_code = {s["code"]: s for s in response.data["data"]["subjects"]}
        assert by_code["MATH"]["can_edit"] is True
        assert by_code["ENG"]["can_edit"] is False

    def test_dos_can_read_any_class(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["dos_user"])
        response = api_client.get(
            "/api/v1/academics/results/class-overview/",
            {
                "term": str(results_setup["term"].id),
                "school_class": str(results_setup["school_class"].id),
            },
        )
        assert response.status_code == 200
        assert response.data["data"]["exam_count"] >= 2

    def test_capabilities_endpoint(self, api_client, results_setup):
        api_client.force_authenticate(user=results_setup["dos_user"])
        response = api_client.get("/api/v1/academics/results/capabilities/")
        assert response.status_code == 200
        data = response.data["data"]
        assert data["can_enter_marks"] is False
        assert data["can_print_report_cards"] is True
        assert data["scope_meta"]["can_enter_marks"] is False
