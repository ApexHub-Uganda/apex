"""Extended Academics B–E tests: DoS ops, Uganda seed, certificates, e2e path."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.academics.models import AssessmentScheme, SubjectCombination
from apps.academics.services.certificates import build_academic_transcript_pdf, build_leaving_certificate_pdf
from apps.academics.services.dos_ops import (
    class_performance_analysis,
    marks_completeness_dashboard,
    report_generation_status,
    teacher_load_report,
    uneb_candidate_export,
)
from apps.academics.services.report_cards import generate_class_report_cards, publish_report_cards
from apps.academics.services.report_pdf import build_report_card_pdf
from apps.academics.services.uganda_seed import seed_uganda_presets
from apps.examinations.constants import MARKS_STATUS_APPROVED
from apps.examinations.models import Exam, Grade, GradingScheme, ReportCard
from apps.subscriptions.services import assign_plan_features
from apps.academics.models import AcademicYear, Class, Stream, Subject, Term
from apps.students.models import Student


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
    term = Term.objects.create(
        tenant=tenant, academic_year=year, name="Term 1", term_number=1,
        start_date="2026-02-01", end_date="2026-04-30", is_current=True,
    )
    c1 = Class.objects.create(tenant=tenant, name="S4", code="S4", academic_year=year, curriculum="uneb")
    st_east = Stream.objects.create(tenant=tenant, school_class=c1, name="East")
    subj = Subject.objects.create(tenant=tenant, name="Mathematics", code="MATH")
    scheme = GradingScheme.objects.create(tenant=tenant, name="Default", is_default=True)
    from apps.examinations.models import GradingSchemeBand
    GradingSchemeBand.objects.create(
        tenant=tenant, scheme=scheme, min_score=0, max_score=49, grade="F9", grade_point=9,
    )
    GradingSchemeBand.objects.create(
        tenant=tenant, scheme=scheme, min_score=50, max_score=100, grade="D1", grade_point=1,
    )
    s1 = Student.objects.create(
        tenant=tenant, admission_number="UG-101", first_name="Amina", last_name="Okello",
        date_of_birth="2010-01-01", gender="female", enrollment_date="2026-02-01",
        school_class=c1, stream=st_east, status="active", nationality="Ugandan",
        registration_number="U001",
    )
    s2 = Student.objects.create(
        tenant=tenant, admission_number="UG-102", first_name="Brian", last_name="Mugisha",
        date_of_birth="2010-03-01", gender="male", enrollment_date="2026-02-01",
        school_class=c1, stream=st_east, status="active", nationality="Ugandan",
        registration_number="U002",
    )
    exam = Exam.objects.create(
        tenant=tenant, name="EOT Math", subject=subj, school_class=c1, term=term,
        exam_date=date(2026, 4, 10), max_score=100, exam_type="final",
        lifecycle_status="published", marks_status=MARKS_STATUS_APPROVED,
    )
    Grade.objects.create(tenant=tenant, exam=exam, student=s1, score=Decimal("80"), grade="D1")
    Grade.objects.create(tenant=tenant, exam=exam, student=s2, score=Decimal("40"), grade="F9")
    return {
        "year": year, "term": term, "c1": c1, "stream": st_east, "subj": subj,
        "s1": s1, "s2": s2, "admin": school_admin, "exam": exam,
    }


@pytest.mark.django_db
class TestDosAndUganda:
    def test_uganda_seed(self, tenant, school_ctx):
        out = seed_uganda_presets(tenant=tenant, user=school_ctx["admin"])
        assert out["assessment_schemes"] >= 1
        assert AssessmentScheme.objects.filter(tenant=tenant).exists()
        assert SubjectCombination.objects.filter(tenant=tenant, code="PCM").exists()

    def test_performance_and_completeness(self, tenant, school_ctx):
        perf = class_performance_analysis(tenant=tenant, term_id=str(school_ctx["term"].id), school_class_id=str(school_ctx["c1"].id))
        assert perf["counts"]["students"] == 2
        assert len(perf["failure_list"]) >= 1
        comp = marks_completeness_dashboard(tenant=tenant, term_id=str(school_ctx["term"].id))
        assert comp["summary"]["total_exams"] >= 1
        load = teacher_load_report(tenant=tenant)
        assert "rows" in load
        st = report_generation_status(tenant=tenant, term_id=str(school_ctx["term"].id))
        assert any(r["status"] == "not_generated" for r in st["rows"])

    def test_uneb_export(self, tenant, school_ctx):
        fname, csv_text = uneb_candidate_export(tenant=tenant, level_hint="uce", exam_year="2026")
        assert "index_number" in csv_text
        assert "UG-101" in csv_text
        assert fname.endswith(".csv")

    def test_e2e_generate_publish_pdf_certificates(self, tenant, school_ctx):
        gen = generate_class_report_cards(
            tenant=tenant, user=school_ctx["admin"],
            term_id=str(school_ctx["term"].id), school_class_id=str(school_ctx["c1"].id),
        )
        assert gen["count"] == 2
        pub = publish_report_cards(
            tenant=tenant, user=school_ctx["admin"],
            term_id=str(school_ctx["term"].id), school_class_id=str(school_ctx["c1"].id),
        )
        assert pub["published"] == 2
        rc = ReportCard.objects.filter(tenant=tenant, is_latest=True, is_published=True).first()
        assert build_report_card_pdf(tenant=tenant, report_card=rc).startswith(b"%PDF")
        leave = build_leaving_certificate_pdf(tenant=tenant, student=school_ctx["s1"], reason="Transfer")
        assert leave.startswith(b"%PDF")
        tr = build_academic_transcript_pdf(tenant=tenant, student=school_ctx["s1"])
        assert tr.startswith(b"%PDF")

    def test_dos_api(self, api_client, school_ctx):
        api_client.force_authenticate(user=school_ctx["admin"])
        r = api_client.get("/api/v1/academics/dos/performance/")
        assert r.status_code == 200
        r = api_client.get("/api/v1/academics/dos/uneb-candidates.csv")
        assert r.status_code == 200
        assert "text/csv" in r["Content-Type"]
        r = api_client.post("/api/v1/academics/uganda-seed/")
        assert r.status_code == 200
