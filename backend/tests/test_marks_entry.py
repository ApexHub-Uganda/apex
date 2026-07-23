"""Marks entry subject-first workflow tests.

Only subject teachers with teaching assignments may enter marks.
School admin and DoS cannot enter marks.
"""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Subject, SubjectPaper, Term, Timetable
from apps.core.constants import UserRole
from apps.examinations.models import Exam, Grade
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def marks_entry_setup(tenant, plan):
    assign_plan_features(plan, [
        "marks_entry", "grade_calculation", "examination_management", "classes",
        "subjects", "terms", "timetables", "result_processing", "report_cards",
    ])
    year = AcademicYear.objects.create(
        tenant=tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=tenant,
        name="Grade 5",
        code="G5",
        academic_year=year,
    )
    subject = Subject.objects.create(tenant=tenant, name="Mathematics", code="MATH")
    SubjectPaper.objects.create(tenant=tenant, subject=subject, code="M223", sort_order=1)
    SubjectPaper.objects.create(tenant=tenant, subject=subject, code="M224", sort_order=2)
    staff = onboard_staff(
        tenant,
        data={
            "first_name": "Subject",
            "last_name": "Teacher",
            "email": "subject.teacher@marks.test",
            "phone": "+256700000901",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    teacher = staff.teacher_profile
    Timetable.objects.create(
        tenant=tenant,
        school_class=school_class,
        subject=subject,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    exam = Exam.objects.create(
        tenant=tenant,
        name="Midterm Maths Paper 1",
        subject=subject,
        paper=subject.papers.first(),
        school_class=school_class,
        term=term,
        exam_date=date(2026, 3, 1),
        max_score=100,
        exam_type="midterm",
        lifecycle_status="published",
    )
    student = Student.objects.create(
        tenant=tenant,
        admission_number="TEST-0001",
        first_name="Alex",
        last_name="Kimani",
        date_of_birth=date(2015, 5, 5),
        gender="male",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    return {
        "subject": subject,
        "school_class": school_class,
        "term": term,
        "exam": exam,
        "student": student,
        "teacher_user": staff.user,
        "teacher": teacher,
        "year": year,
    }


@pytest.mark.django_db
class TestMarksEntry:
    def test_options_start_with_subjects_for_subject_teacher(self, api_client, marks_entry_setup):
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        response = api_client.get("/api/v1/examinations/marks-entry/options/")
        assert response.status_code == 200
        subjects = response.data["data"]["subjects"]
        assert any(s["value"] == str(marks_entry_setup["subject"].id) for s in subjects)
        subject_row = next(s for s in subjects if s["value"] == str(marks_entry_setup["subject"].id))
        assert subject_row["has_papers"] is True
        assert len(subject_row["papers"]) == 2
        assert response.data["data"]["scope_meta"]["can_enter_marks"] is True
        assert response.data["data"]["scope_meta"]["is_unrestricted"] is False

    def test_school_admin_cannot_enter_marks(self, api_client, school_admin, marks_entry_setup):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/examinations/marks-entry/options/")
        assert response.status_code == 200
        data = response.data["data"]
        assert data["scope_meta"]["can_enter_marks"] is False
        assert data["subjects"] == []

        bulk = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {
                "exam": str(marks_entry_setup["exam"].id),
                "entries": [{"student": str(marks_entry_setup["student"].id), "score": 90}],
            },
            format="json",
        )
        assert bulk.status_code == 403

    def test_classes_from_teaching_assignment(self, api_client, marks_entry_setup, tenant):
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        Exam.objects.all().delete()
        subject_id = marks_entry_setup["subject"].id
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {"subject": subject_id},
        )
        assert response.status_code == 200
        classes = response.data["data"]["classes"]
        assert len(classes) == 1
        assert classes[0]["value"] == str(marks_entry_setup["school_class"].id)

    def test_current_term_auto_applied_without_term_param(self, api_client, marks_entry_setup):
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "school_class": marks_entry_setup["school_class"].id,
            },
        )
        assert response.status_code == 200
        data = response.data["data"]
        assert data["scope_meta"]["current_term_id"] == str(marks_entry_setup["term"].id)
        assert data["current_term"]["value"] == str(marks_entry_setup["term"].id)
        assert data["auto_select"]["term"] == str(marks_entry_setup["term"].id)
        # Papered exams must appear even when paper is not selected (previous bug hid them)
        exam_ids = {e["value"] for e in data["exams"]}
        assert str(marks_entry_setup["exam"].id) in exam_ids

    def test_options_return_students_when_exam_selected(self, api_client, marks_entry_setup):
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        paper = marks_entry_setup["subject"].papers.first()
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "paper": paper.id,
                "school_class": marks_entry_setup["school_class"].id,
                "exam": marks_entry_setup["exam"].id,
            },
        )
        assert response.status_code == 200
        students = response.data["data"]["students"]
        assert len(students) == 1
        assert students[0]["admission_number"] == "TEST-0001"

    def test_draft_scheduled_exam_visible_to_teacher(self, api_client, marks_entry_setup, tenant):
        """DoS/admin schedules as draft — teacher still sees it for marks entry."""
        exam = marks_entry_setup["exam"]
        exam.lifecycle_status = "draft"
        exam.save(update_fields=["lifecycle_status"])
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "school_class": marks_entry_setup["school_class"].id,
            },
        )
        assert response.status_code == 200
        exam_ids = {e["value"] for e in response.data["data"]["exams"]}
        assert str(exam.id) in exam_ids

    def test_active_exam_period_auto_provisions_mark_sheet(
        self, api_client, marks_entry_setup, tenant,
    ):
        """
        Exam Session alone is enough: when a teacher picks subject+class during
        an active period, a mark sheet is created automatically.
        """
        from apps.examinations.models import ExaminationSession

        Exam.objects.filter(tenant=tenant).delete()
        ExaminationSession.objects.create(
            tenant=tenant,
            name="End of Term One",
            academic_year=marks_entry_setup["year"],
            term=marks_entry_setup["term"],
            start_date=date(2026, 7, 18),
            end_date=date(2026, 7, 30),
            status="active",
        )
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "school_class": marks_entry_setup["school_class"].id,
            },
        )
        assert response.status_code == 200
        data = response.data["data"]
        assert data["scope_meta"]["has_active_exam_period"] is True
        assert data["scope_meta"]["active_exam_period"]["name"] == "End of Term One"
        assert len(data["exams"]) >= 1
        assert data["auto_select"]["exam"]
        # Sheet is ready for marks
        exam = Exam.objects.get(pk=data["auto_select"]["exam"])
        assert exam.examination_session_id is not None
        assert exam.lifecycle_status == "published"

        # Open students grid
        students_resp = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "school_class": marks_entry_setup["school_class"].id,
                "exam": exam.id,
            },
        )
        assert students_resp.status_code == 200
        assert len(students_resp.data["data"]["students"]) == 1

    def test_bulk_save_and_delete_marks_as_subject_teacher(self, api_client, marks_entry_setup, tenant):
        api_client.force_authenticate(user=marks_entry_setup["teacher_user"])
        exam = marks_entry_setup["exam"]
        student = marks_entry_setup["student"]
        response = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {
                "exam": str(exam.id),
                "entries": [{"student": str(student.id), "score": 88, "remarks": "Strong work"}],
            },
            format="json",
        )
        assert response.status_code == 200
        grade = Grade.objects.get(tenant=tenant, exam=exam, student=student, is_deleted=False)
        assert float(grade.score) == 88.0
        assert grade.remarks == "Strong work"

        # Clear score soft-deletes the mark (subject teacher only)
        clear = api_client.post(
            "/api/v1/examinations/marks-entry/bulk/",
            {
                "exam": str(exam.id),
                "entries": [{"student": str(student.id), "score": None}],
            },
            format="json",
        )
        assert clear.status_code == 200
        grade.refresh_from_db()
        assert grade.is_deleted is True

    def test_subject_paper_codes_on_create(self, api_client, school_admin, plan, tenant):
        assign_plan_features(plan, ["subjects"])
        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/academics/subjects/",
            {
                "name": "Physics",
                "code": "PHY",
                "paper_codes": "P223, P224",
            },
            format="json",
        )
        assert response.status_code == 201
        subject = Subject.objects.get(code="PHY")
        assert list(subject.papers.values_list("code", flat=True)) == ["P223", "P224"]
