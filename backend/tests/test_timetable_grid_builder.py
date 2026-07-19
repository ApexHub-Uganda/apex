"""Class-by-class timetable grid builder + print tests."""
from __future__ import annotations

import pytest

from apps.academics.models import AcademicYear, Class, Period, Subject, TeachingAssignment, Term, Timetable
from apps.academics.services.timetable_builder import (
    bulk_sync_periods,
    get_class_grid,
    save_class_grid,
    validate_grid_cells,
)
from apps.academics.services.timetable_pdf import build_timetable_pdf
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features
from apps.students.models import Student  # noqa: F401 — ensure student app ready


@pytest.fixture
def tt_plan(db, plan):
    assign_plan_features(plan, [
        "timetables", "periods", "classes", "subjects", "subject_assignment",
        "teacher_assignments", "academic_years", "terms", "staff_management",
    ])
    return plan


@pytest.fixture
def tt_ctx(db, tenant, tt_plan, school_admin):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    term = Term.objects.create(
        tenant=tenant, academic_year=year, name="Term 1", term_number=1,
        start_date="2026-02-01", end_date="2026-04-30", is_current=True,
    )
    c1 = Class.objects.create(tenant=tenant, name="S1 East", code="S1E", academic_year=year, curriculum="uneb")
    c2 = Class.objects.create(tenant=tenant, name="S1 West", code="S1W", academic_year=year, curriculum="uneb")
    math = Subject.objects.create(tenant=tenant, name="Mathematics", code="MATH")
    eng = Subject.objects.create(tenant=tenant, name="English", code="ENG")

    from apps.core.constants import UserRole
    from apps.staff.models import Teacher

    staff1 = onboard_staff(
        tenant,
        data={
            "first_name": "Mary",
            "last_name": "Teacher",
            "email": "mary.tt@example.com",
            "phone": "+256700000001",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2020-01-01",
        },
    )
    teacher = getattr(staff1, "teacher_profile", None) or Teacher.objects.filter(tenant=tenant, staff=staff1).first()
    if teacher is None:
        teacher = Teacher.objects.create(tenant=tenant, staff=staff1)

    TeachingAssignment.objects.create(
        tenant=tenant, teacher=teacher, school_class=c1, subject=math, academic_year=year, is_active=True,
    )
    TeachingAssignment.objects.create(
        tenant=tenant, teacher=teacher, school_class=c2, subject=eng, academic_year=year, is_active=True,
    )

    periods = bulk_sync_periods(
        tenant=tenant,
        user=school_admin,
        periods_payload=[
            {"name": "P1", "start_time": "08:00", "end_time": "08:40", "sort_order": 1, "is_break": False},
            {"name": "Break", "start_time": "08:40", "end_time": "09:00", "sort_order": 2, "is_break": True},
            {"name": "P2", "start_time": "09:00", "end_time": "09:40", "sort_order": 3, "is_break": False},
        ],
    )
    return {
        "year": year, "term": term, "c1": c1, "c2": c2, "math": math, "eng": eng,
        "teacher": teacher, "admin": school_admin, "periods": periods,
    }


@pytest.mark.django_db
class TestTimetableGridBuilder:
    def test_periods_same_for_all_days(self, tenant, tt_ctx):
        assert Period.objects.filter(tenant=tenant, is_deleted=False).count() == 3
        p1 = Period.objects.get(tenant=tenant, name="P1")
        assert str(p1.start_time)[:5] == "08:00"
        assert Period.objects.get(tenant=tenant, name="Break").is_break

    def test_class_grid_empty_then_save(self, tenant, tt_ctx):
        grid = get_class_grid(
            tenant=tenant,
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            working_days=[0, 1, 2, 3, 4],
        )
        assert len(grid["periods"]) == 3
        assert any(c["is_break"] for c in grid["cells"])
        # Fill Mon P1 with Math
        p1 = next(p for p in grid["periods"] if p["name"] == "P1")
        cells = []
        for cell in grid["cells"]:
            if cell["day_of_week"] == 0 and cell["period_id"] == p1["id"] and not cell["is_break"]:
                cells.append({
                    **cell,
                    "subject_id": str(tt_ctx["math"].id),
                    "teacher_id": str(tt_ctx["teacher"].id),
                    "is_empty": False,
                })
            else:
                cells.append(cell)
        out = save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=cells,
        )
        assert out["entries_created"] >= 1
        assert Timetable.objects.filter(
            tenant=tenant, school_class=tt_ctx["c1"], subject=tt_ctx["math"], is_deleted=False,
        ).exists()

    def test_teacher_clash_only_from_published(self, tenant, tt_ctx):
        """Concurrent writers only inherit constraints from *published* schedules."""
        from apps.academics.services.timetable_builder import publish_timetable_schedule

        p1 = Period.objects.get(tenant=tenant, name="P1")
        # Save class1 Mon P1 as draft — should NOT clash yet
        out = save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=[{
                "day_of_week": 0,
                "period_id": str(p1.id),
                "subject_id": str(tt_ctx["math"].id),
                "teacher_id": str(tt_ctx["teacher"].id),
                "is_break": False,
            }],
        )
        draft_cells = [{
            "day_of_week": 0,
            "period_id": str(p1.id),
            "subject_id": str(tt_ctx["eng"].id),
            "teacher_id": str(tt_ctx["teacher"].id),
            "teacher_name": "Mary Teacher",
            "period_name": "P1",
            "is_break": False,
        }]
        v_draft = validate_grid_cells(
            tenant=tenant,
            school_class_id=str(tt_ctx["c2"].id),
            term_id=str(tt_ctx["term"].id),
            cells=draft_cells,
        )
        assert v_draft["ok"] is True, "drafts must not constrain other writers"

        publish_timetable_schedule(
            tenant=tenant,
            user=tt_ctx["admin"],
            schedule_id=out["schedule_id"],
        )
        v = validate_grid_cells(
            tenant=tenant,
            school_class_id=str(tt_ctx["c2"].id),
            term_id=str(tt_ctx["term"].id),
            cells=draft_cells,
        )
        assert v["ok"] is False
        clash = next(c for c in v["conflicts"] if c["type"] == "teacher_clash")
        assert "published" in clash["message"].lower()

    def test_print_pdf_landscape(self, tenant, tt_ctx):
        p1 = Period.objects.get(tenant=tenant, name="P1")
        save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=[{
                "day_of_week": 0,
                "period_id": str(p1.id),
                "subject_id": str(tt_ctx["math"].id),
                "teacher_id": str(tt_ctx["teacher"].id),
                "is_break": False,
            }],
        )
        from apps.academics.services.timetable_pdf import (
            _cell_parts, _index_entries, _load_entries, _lookup_entry,
        )
        entries = _load_entries(
            tenant=tenant, term=tt_ctx["term"], class_ids=[str(tt_ctx["c1"].id)],
        )
        assert len(entries) >= 1
        assert any(e.subject_id == tt_ctx["math"].id for e in entries)
        index = _index_entries(entries)
        hit = _lookup_entry(index, str(tt_ctx["c1"].id), 0, p1)
        assert hit is not None
        parts = _cell_parts(hit)
        assert any("Math" in x or "MATH" in x for x in parts)

        pdf = build_timetable_pdf(
            tenant=tenant,
            term_id=str(tt_ctx["term"].id),
            class_ids=[str(tt_ctx["c1"].id)],
            orientation="landscape",
        )
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 500

    def test_wizard_api(self, api_client, tt_ctx):
        api_client.force_authenticate(user=tt_ctx["admin"])
        r = api_client.get("/api/v1/academics/timetables/wizard/context/")
        assert r.status_code == 200
        assert r.data["data"]["readiness"]["has_periods"]
        r = api_client.get("/api/v1/academics/timetables/wizard/grid/", {
            "school_class": str(tt_ctx["c1"].id),
            "term": str(tt_ctx["term"].id),
        })
        assert r.status_code == 200
        assert len(r.data["data"]["cells"]) > 0

    def test_simple_period_save_and_overlap_message(self, api_client, tenant, tt_ctx):
        api_client.force_authenticate(user=tt_ctx["admin"])
        # Simple non-overlapping — like Periods page
        r = api_client.post("/api/v1/academics/timetables/wizard/periods/", {
            "periods": [
                {"name": "P1", "start_time": "08:00", "end_time": "08:40", "is_break": False},
                {"name": "P2", "start_time": "08:40", "end_time": "09:20", "is_break": False},
            ],
        }, format="json")
        assert r.status_code == 200, r.data
        assert len(r.data["data"]["periods"]) == 2
        # Overlap should return a clear message (not generic "Invalid periods.")
        r2 = api_client.post("/api/v1/academics/timetables/wizard/periods/", {
            "periods": [
                {"name": "A", "start_time": "08:00", "end_time": "09:00", "is_break": False},
                {"name": "B", "start_time": "08:30", "end_time": "09:30", "is_break": False},
            ],
        }, format="json")
        assert r2.status_code == 400
        assert "overlap" in (r2.data.get("message") or "").lower()

    def test_create_draft_appears_and_save_binds_to_it(self, api_client, tenant, tt_ctx):
        api_client.force_authenticate(user=tt_ctx["admin"])
        r = api_client.post("/api/v1/academics/timetables/wizard/create-draft/", {
            "term": str(tt_ctx["term"].id),
            "name": "My Pilot Draft",
        }, format="json")
        assert r.status_code == 201, r.data
        draft_id = r.data["data"]["id"]
        rlist = api_client.get("/api/v1/academics/timetable-schedules/")
        assert rlist.status_code == 200
        ids = [s["id"] for s in rlist.data["data"]]
        assert draft_id in ids
        p1 = Period.objects.filter(tenant=tenant, name="P1").first()
        cells = [{
            "day_of_week": 0,
            "period_id": str(p1.id),
            "subject_id": str(tt_ctx["math"].id),
            "teacher_id": str(tt_ctx["teacher"].id),
            "is_break": False,
            "subject_name": "Mathematics",
            "teacher_name": "Mary Teacher",
        }]
        rsave = api_client.post("/api/v1/academics/timetables/wizard/grid/", {
            "school_class": str(tt_ctx["c1"].id),
            "term": str(tt_ctx["term"].id),
            "schedule_id": draft_id,
            "cells": cells,
            "force": True,
        }, format="json")
        assert rsave.status_code == 200, rsave.data
        assert rsave.data["data"]["schedule_id"] == draft_id
        assert rsave.data["data"]["subjects_saved"] >= 1
        # Second draft is independent
        r2 = api_client.post("/api/v1/academics/timetables/wizard/create-draft/", {
            "term": str(tt_ctx["term"].id),
        }, format="json")
        assert r2.status_code == 201
        assert r2.data["data"]["id"] != draft_id

    def test_print_pdf_teacher_highlight_and_mine_only(self, tenant, tt_ctx):
        """Teacher personal views: highlight mine / blank others."""
        p1 = Period.objects.get(tenant=tenant, name="P1")
        p2 = Period.objects.filter(tenant=tenant, name="P2").first()
        out = save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=[
                {
                    "day_of_week": 0,
                    "period_id": str(p1.id),
                    "subject_id": str(tt_ctx["math"].id),
                    "teacher_id": str(tt_ctx["teacher"].id),
                    "is_break": False,
                    "subject_name": "Mathematics",
                    "teacher_name": "Mary Teacher",
                },
            ],
        )
        # Another teacher on another class
        from apps.core.constants import UserRole
        from apps.staff.models import Teacher
        from apps.staff.services import onboard_staff
        staff2 = onboard_staff(
            tenant,
            data={
                "first_name": "Other",
                "last_name": "Tutor",
                "email": "other.tt@example.com",
                "phone": "+256700000088",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2020-01-01",
            },
        )
        t2 = getattr(staff2, "teacher_profile", None) or Teacher.objects.filter(
            tenant=tenant, staff=staff2,
        ).first()
        if t2 is None:
            t2 = Teacher.objects.create(tenant=tenant, staff=staff2)
        save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c2"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            schedule_id=out["schedule_id"],
            cells=[{
                "day_of_week": 0,
                "period_id": str(p1.id),
                "subject_id": str(tt_ctx["eng"].id),
                "teacher_id": str(t2.id),
                "is_break": False,
                "subject_name": "English",
                "teacher_name": "Other Tutor",
            }],
            force=True,
        )
        pdf_hi = build_timetable_pdf(
            tenant=tenant,
            schedule_id=out["schedule_id"],
            orientation="landscape",
            teacher_mode="highlight",
            teacher_id=str(tt_ctx["teacher"].id),
        )
        assert pdf_hi.startswith(b"%PDF")
        pdf_mine = build_timetable_pdf(
            tenant=tenant,
            schedule_id=out["schedule_id"],
            orientation="landscape",
            teacher_mode="mine_only",
            teacher_id=str(tt_ctx["teacher"].id),
        )
        assert pdf_mine.startswith(b"%PDF")
        assert len(pdf_mine) > 500

    def test_print_pdf_embeds_qr_meta(self, tenant, tt_ctx):
        """Branded PDF carries QR payload with scope / creator / schedule meta."""
        from apps.academics.models import TimetableSchedule
        from apps.core.pdf_template import encode_document_qr_payload, _make_qr_image

        p1 = Period.objects.get(tenant=tenant, name="P1")
        out = save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=[{
                "day_of_week": 0,
                "period_id": str(p1.id),
                "subject_id": str(tt_ctx["math"].id),
                "teacher_id": str(tt_ctx["teacher"].id),
                "is_break": False,
                "subject_name": "Mathematics",
                "teacher_name": "Mary Teacher",
            }],
        )
        pdf = build_timetable_pdf(
            tenant=tenant,
            term_id=str(tt_ctx["term"].id),
            class_ids=[str(tt_ctx["c1"].id)],
            orientation="landscape",
            schedule_id=out["schedule_id"],
        )
        assert pdf.startswith(b"%PDF")
        # QR image generator must succeed for timetable meta
        payload = encode_document_qr_payload(
            branding={"school_code": "TST", "school_id": str(tenant.id), "school_name": "Test"},
            document_type="timetable",
            document_meta={
                "name": "Term 1 Timetable",
                "status": "published",
                "term": "Term 1",
                "class": "S1 East",
            },
        )
        # Compact professional payload only
        assert "TST" in payload
        assert "Term 1 Timetable" in payload
        assert "published" in payload
        assert "S1 East" in payload
        assert "schedule_id" not in payload
        assert "created_by" not in payload
        img = _make_qr_image(payload)
        assert img is not None
        assert img.size[0] >= 50

    def test_exam_timetable_save_print_and_constraints(self, api_client, tenant, tt_ctx):
        """Exam slots use date+time, free teacher pick, published constraints, QR PDF."""
        from apps.academics.services.exam_timetable import (
            build_exam_timetable_pdf,
            create_draft_exam_schedule,
            publish_exam_schedule,
            save_exam_slots,
            validate_exam_slots,
        )
        from apps.academics.services.timetable_builder import publish_timetable_schedule
        from apps.core.constants import UserRole
        from apps.staff.models import Teacher
        from apps.staff.services import onboard_staff

        api_client.force_authenticate(user=tt_ctx["admin"])
        # Context endpoint
        r = api_client.get("/api/v1/academics/timetables/exam/context/")
        assert r.status_code == 200, r.data
        assert "teachers" in r.data["data"]
        assert "classes" in r.data["data"]

        # Publish a lesson so exam validation can see it
        p1 = Period.objects.get(tenant=tenant, name="P1")
        lesson = save_class_grid(
            tenant=tenant,
            user=tt_ctx["admin"],
            school_class_id=str(tt_ctx["c1"].id),
            term_id=str(tt_ctx["term"].id),
            stream_id=None,
            cells=[{
                "day_of_week": 0,  # Monday
                "period_id": str(p1.id),
                "subject_id": str(tt_ctx["math"].id),
                "teacher_id": str(tt_ctx["teacher"].id),
                "is_break": False,
            }],
        )
        publish_timetable_schedule(
            tenant=tenant, user=tt_ctx["admin"], schedule_id=lesson["schedule_id"],
        )

        staff2 = onboard_staff(
            tenant,
            data={
                "first_name": "John",
                "last_name": "Invigilator",
                "email": "john.inv@example.com",
                "phone": "+256700000099",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2020-01-01",
            },
        )
        invig = getattr(staff2, "teacher_profile", None) or Teacher.objects.filter(
            tenant=tenant, staff=staff2,
        ).first()
        if invig is None:
            invig = Teacher.objects.create(tenant=tenant, staff=staff2)

        schedule = create_draft_exam_schedule(
            tenant=tenant,
            user=tt_ctx["admin"],
            term_id=str(tt_ctx["term"].id),
            name="Midterm Exam TT",
        )
        # Monday 2026-02-02 is a Monday — same weekday as published lesson P1 08:00
        slots = [{
            "exam_date": "2026-02-02",
            "start_time": "08:00",
            "end_time": "10:00",
            "school_class_id": str(tt_ctx["c1"].id),
            "subject_id": str(tt_ctx["math"].id),
            "teacher_id": str(tt_ctx["teacher"].id),  # same teacher as published lesson
            "teacher_name": "Mary Teacher",
            "subject_name": "Mathematics",
            "room": "Hall A",
        }]
        v = validate_exam_slots(tenant=tenant, slots=slots, schedule_id=str(schedule.id))
        assert v["ok"] is False
        assert any("published" in c["message"].lower() or "lesson" in c["message"].lower() for c in v["conflicts"])

        # Free-picked different invigilator — should be fine
        slots[0]["teacher_id"] = str(invig.id)
        slots[0]["teacher_name"] = "John Invigilator"
        saved = save_exam_slots(
            tenant=tenant,
            user=tt_ctx["admin"],
            schedule_id=str(schedule.id),
            slots=slots,
        )
        assert saved["entries_created"] == 1

        pub = publish_exam_schedule(
            tenant=tenant, user=tt_ctx["admin"], schedule_id=str(schedule.id),
        )
        assert pub["is_published"] is True
        assert pub["schedule_type"] == "exam"

        pdf = build_exam_timetable_pdf(
            tenant=tenant, schedule_id=str(schedule.id), orientation="landscape",
        )
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 500

        # API create + list filter
        r2 = api_client.post("/api/v1/academics/timetables/exam/create-draft/", {
            "term": str(tt_ctx["term"].id),
            "name": "API Exam Draft",
        }, format="json")
        assert r2.status_code == 201, r2.data
        rlist = api_client.get("/api/v1/academics/timetable-schedules/", {"schedule_type": "exam"})
        assert rlist.status_code == 200
        exam_ids = [s["id"] for s in rlist.data["data"]]
        assert r2.data["data"]["id"] in exam_ids
        assert str(schedule.id) in exam_ids
