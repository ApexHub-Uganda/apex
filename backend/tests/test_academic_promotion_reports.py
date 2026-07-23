"""Promotion + report card generation pipeline tests."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, AssessmentScheme, Class, Stream, Subject, TeachingAssignment, Term
from apps.academics.services.promotion import commit_promotion, preview_promotion
from apps.academics.services.report_cards import generate_class_report_cards, publish_report_cards
from apps.academics.services.report_pdf import build_report_card_pdf
from apps.core.constants import UserRole
from apps.examinations.constants import MARKS_STATUS_APPROVED
from apps.examinations.models import Exam, Grade, GradingScheme, GradingSchemeBand, ReportCard
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def academic_plan(db, plan):
    assign_plan_features(plan, [
        "academic_years", "terms", "classes", "subjects", "subject_assignment",
        "student_promotion", "report_cards", "class_report_cards", "result_processing",
        "grading", "marks_entry", "dos_workspace", "student_management", "staff_management",
        "examination_management", "grade_calculation",
    ])
    return plan


@pytest.fixture
def school_ctx(db, tenant, academic_plan, school_admin):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    year2 = AcademicYear.objects.create(
        tenant=tenant, name="2027", start_date="2027-01-01", end_date="2027-12-31", is_current=False,
    )
    term = Term.objects.create(
        tenant=tenant, academic_year=year, name="Term 1", term_number=1,
        start_date="2026-02-01", end_date="2026-04-30", is_current=True,
    )
    c1 = Class.objects.create(tenant=tenant, name="S1", code="S1", academic_year=year, curriculum="uneb")
    c2 = Class.objects.create(tenant=tenant, name="S2", code="S2", academic_year=year2, curriculum="uneb")
    st_east = Stream.objects.create(tenant=tenant, school_class=c1, name="East")
    Stream.objects.create(tenant=tenant, school_class=c2, name="East")
    subj = Subject.objects.create(tenant=tenant, name="Mathematics", code="MATH")
    scheme = GradingScheme.objects.create(tenant=tenant, name="Default", is_default=True)
    GradingSchemeBand.objects.create(
        tenant=tenant, scheme=scheme, min_score=0, max_score=49, grade="F9", grade_point=0,
    )
    GradingSchemeBand.objects.create(
        tenant=tenant, scheme=scheme, min_score=50, max_score=100, grade="D1", grade_point=1,
    )
    AssessmentScheme.objects.create(
        tenant=tenant, name="BOT/MOT/EOT", is_default=True,
        components=[
            {"key": "bot", "label": "BOT", "weight_percent": 15},
            {"key": "mot", "label": "MOT", "weight_percent": 15},
            {"key": "eot", "label": "EOT", "weight_percent": 70},
        ],
    )
    s1 = Student.objects.create(
        tenant=tenant, admission_number="UG-001", first_name="Amina", last_name="Okello",
        date_of_birth="2012-01-01", gender="female", enrollment_date="2026-02-01",
        school_class=c1, stream=st_east, status="active", nationality="Ugandan",
    )
    s2 = Student.objects.create(
        tenant=tenant, admission_number="UG-002", first_name="Brian", last_name="Mugisha",
        date_of_birth="2012-03-01", gender="male", enrollment_date="2026-02-01",
        school_class=c1, stream=st_east, status="active", nationality="Ugandan",
    )
    exam = Exam.objects.create(
        tenant=tenant, name="EOT Math", subject=subj, school_class=c1, term=term,
        exam_date=date(2026, 4, 10), max_score=100, exam_type="final",
        lifecycle_status="published", marks_status=MARKS_STATUS_APPROVED,
    )
    Grade.objects.create(tenant=tenant, exam=exam, student=s1, score=Decimal("80"), grade="D1")
    Grade.objects.create(tenant=tenant, exam=exam, student=s2, score=Decimal("55"), grade="D1")
    return {
        "year": year, "year2": year2, "term": term, "c1": c1, "c2": c2,
        "stream": st_east, "subj": subj, "s1": s1, "s2": s2, "admin": school_admin,
    }


@pytest.mark.django_db
class TestPromotionAndReports:
    def test_promote_class_moves_students(self, tenant, school_ctx):
        preview = preview_promotion(
            tenant=tenant,
            user=school_ctx["admin"],
            source_class_id=str(school_ctx["c1"].id),
            target_class_id=str(school_ctx["c2"].id),
            target_academic_year_id=str(school_ctx["year2"].id),
        )
        assert preview["preview"]["count"] == 2
        result = commit_promotion(
            tenant=tenant, user=school_ctx["admin"], batch_id=preview["batch_id"],
        )
        assert result["applied"] == 2
        school_ctx["s1"].refresh_from_db()
        assert school_ctx["s1"].school_class_id == school_ctx["c2"].id

    def test_hold_and_graduate_actions(self, tenant, school_ctx):
        preview = preview_promotion(
            tenant=tenant,
            user=school_ctx["admin"],
            source_class_id=str(school_ctx["c1"].id),
            target_class_id=str(school_ctx["c2"].id),
            actions=[
                {"student_id": str(school_ctx["s1"].id), "action": "hold"},
                {"student_id": str(school_ctx["s2"].id), "action": "graduate"},
            ],
        )
        commit_promotion(tenant=tenant, user=school_ctx["admin"], batch_id=preview["batch_id"])
        school_ctx["s1"].refresh_from_db()
        school_ctx["s2"].refresh_from_db()
        assert school_ctx["s1"].school_class_id == school_ctx["c1"].id
        assert school_ctx["s2"].status == "graduated"
        assert school_ctx["s2"].school_class_id is None

    def test_generate_and_publish_report_cards_pdf(self, tenant, school_ctx):
        out = generate_class_report_cards(
            tenant=tenant,
            user=school_ctx["admin"],
            term_id=str(school_ctx["term"].id),
            school_class_id=str(school_ctx["c1"].id),
        )
        assert out["count"] == 2
        cards = ReportCard.objects.filter(tenant=tenant, is_latest=True)
        assert cards.count() == 2
        assert cards.filter(rank=1).exists()
        rc = cards.select_related("student").prefetch_related("subject_lines").first()
        assert rc.subject_lines.count() >= 1
        pdf = build_report_card_pdf(tenant=tenant, report_card=rc)
        assert pdf.startswith(b"%PDF")
        pub = publish_report_cards(tenant=tenant, user=school_ctx["admin"], term_id=str(school_ctx["term"].id), school_class_id=str(school_ctx["c1"].id))
        assert pub["published"] == 2
        assert ReportCard.objects.filter(is_published=True, is_latest=True).count() == 2

    def test_promotion_api(self, api_client, tenant, school_ctx):
        api_client.force_authenticate(user=school_ctx["admin"])
        r = api_client.get("/api/v1/academics/promotion/context/")
        assert r.status_code == 200
        classes = r.data["data"]["classes"]
        assert any("is_terminal" in c for c in classes)
        r = api_client.post("/api/v1/academics/promotion/preview/", {
            "source_class": str(school_ctx["c1"].id),
            "target_class": str(school_ctx["c2"].id),
            "target_academic_year": str(school_ctx["year2"].id),
        }, format="json")
        assert r.status_code == 200, r.data
        batch_id = r.data["data"]["batch_id"]
        r2 = api_client.post(
            f"/api/v1/academics/promotion/{batch_id}/commit/",
            {"issue_certificates": True},
            format="json",
        )
        assert r2.status_code == 200

    def test_terminal_class_defaults_to_graduate(self, tenant, school_admin):
        from apps.academics.models import AcademicYear, Class
        from apps.academics.services.promotion import is_terminal_class, preview_promotion
        from apps.students.models import Student
        from datetime import date

        year = AcademicYear.objects.create(
            tenant=tenant, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True,
        )
        p7 = Class.objects.create(
            tenant=tenant, name="Primary 7", code="P7", academic_year=year, level_type="primary",
        )
        assert is_terminal_class(p7) is True
        s = Student.objects.create(
            tenant=tenant, admission_number="P7-1", first_name="Top", last_name="Class",
            date_of_birth=date(2012, 1, 1), gender="male", school_class=p7,
            enrollment_date=date(2026, 1, 1), status="active",
        )
        preview = preview_promotion(
            tenant=tenant, user=school_admin, source_class_id=str(p7.id),
        )
        assert preview["progression"]["is_terminal"] is True
        assert preview["preview"]["graduate"] == 1
        assert all(r["action"] == "graduate" for r in preview["rows"])
        assert s.admission_number == "P7-1"

    def test_completion_certificate_pdf(self, tenant, school_ctx):
        from apps.academics.services.certificates import build_completion_certificate_pdf

        pdf = build_completion_certificate_pdf(
            tenant=tenant,
            student=school_ctx["s1"],
            final_class_name=school_ctx["c1"].name,
            academic_year_name=school_ctx["year"].name,
        )
        assert pdf.startswith(b"%PDF")

    def test_report_generate_api(self, api_client, school_ctx):
        api_client.force_authenticate(user=school_ctx["admin"])
        r = api_client.post("/api/v1/academics/report-cards/generate/", {
            "term": str(school_ctx["term"].id),
            "school_class": str(school_ctx["c1"].id),
        }, format="json")
        assert r.status_code == 200, r.data
        assert r.data["data"]["count"] == 2
