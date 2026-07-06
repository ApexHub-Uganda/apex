"""Marks entry subject-first workflow tests."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Subject, SubjectPaper, Term, Timetable
from apps.examinations.models import Exam, Grade
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def marks_entry_setup(tenant, plan):
    assign_plan_features(plan, [
        "marks_entry", "examination_management", "classes", "subjects", "terms", "timetables",
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
    Timetable.objects.create(
        tenant=tenant,
        school_class=school_class,
        subject=subject,
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
    }


@pytest.mark.django_db
class TestMarksEntry:
    def test_options_start_with_subjects(self, api_client, school_admin, marks_entry_setup):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/examinations/marks-entry/options/")
        assert response.status_code == 200
        subjects = response.data["data"]["subjects"]
        assert any(s["value"] == str(marks_entry_setup["subject"].id) for s in subjects)
        subject_row = next(s for s in subjects if s["value"] == str(marks_entry_setup["subject"].id))
        assert subject_row["has_papers"] is True
        assert len(subject_row["papers"]) == 2

    def test_classes_from_timetable_without_exam(self, api_client, school_admin, marks_entry_setup, tenant):
        api_client.force_authenticate(user=school_admin)
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

    def test_terms_from_school_calendar(self, api_client, school_admin, marks_entry_setup):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "school_class": marks_entry_setup["school_class"].id,
            },
        )
        assert response.status_code == 200
        terms = response.data["data"]["terms"]
        assert len(terms) == 1
        assert terms[0]["value"] == str(marks_entry_setup["term"].id)

    def test_subjects_readable_with_examination_feature_only(self, api_client, school_admin, plan, marks_entry_setup):
        assign_plan_features(plan, ["examination_management"])
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/academics/subjects/")
        assert response.status_code == 200

    def test_options_return_students_when_exam_selected(self, api_client, school_admin, marks_entry_setup):
        api_client.force_authenticate(user=school_admin)
        paper = marks_entry_setup["subject"].papers.first()
        response = api_client.get(
            "/api/v1/examinations/marks-entry/options/",
            {
                "subject": marks_entry_setup["subject"].id,
                "paper": paper.id,
                "school_class": marks_entry_setup["school_class"].id,
                "term": marks_entry_setup["term"].id,
                "exam": marks_entry_setup["exam"].id,
            },
        )
        assert response.status_code == 200
        students = response.data["data"]["students"]
        assert len(students) == 1
        assert students[0]["admission_number"] == "TEST-0001"

    def test_bulk_save_marks(self, api_client, school_admin, marks_entry_setup, tenant):
        api_client.force_authenticate(user=school_admin)
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
        grade = Grade.objects.get(tenant=tenant, exam=exam, student=student)
        assert float(grade.score) == 88.0
        assert grade.remarks == "Strong work"

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