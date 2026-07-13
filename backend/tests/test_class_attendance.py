"""Teacher class attendance marking — class/stream scoped bulk save."""
from __future__ import annotations

from datetime import date

import pytest

from apps.academics.models import AcademicYear, Class, Stream, Subject, Timetable
from apps.attendance.models import AttendanceRecord
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def class_attendance_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Class Attendance Plan", slug="class-attendance-plan", max_students=500)
    assign_plan_features(plan, [
        "student_attendance", "classes", "subjects", "student_management", "academic_years",
    ])
    return plan


@pytest.fixture
def class_attendance_tenant(db, class_attendance_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Attendance School",
        code="ATTN",
        email="attn@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=class_attendance_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def class_attendance_teacher(db, class_attendance_tenant):
    return onboard_staff(
        class_attendance_tenant,
        data={
            "first_name": "Roll",
            "last_name": "Teacher",
            "email": "roll.teacher@test.edu",
            "phone": "+254700000501",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def class_attendance_setup(db, class_attendance_tenant, class_attendance_teacher):
    year = AcademicYear.objects.create(
        tenant=class_attendance_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    class_a = Class.objects.create(
        tenant=class_attendance_tenant, name="Grade 5", code="G5", academic_year=year,
    )
    class_b = Class.objects.create(
        tenant=class_attendance_tenant, name="Grade 6", code="G6", academic_year=year,
    )
    subject = Subject.objects.create(tenant=class_attendance_tenant, name="Mathematics", code="MATH")
    teacher = class_attendance_teacher.teacher_profile
    Timetable.objects.create(
        tenant=class_attendance_tenant,
        school_class=class_a,
        subject=subject,
        teacher=teacher,
        day_of_week=0,
        start_time="08:00",
        end_time="09:00",
    )
    Timetable.objects.create(
        tenant=class_attendance_tenant,
        school_class=class_b,
        subject=subject,
        teacher=teacher,
        day_of_week=1,
        start_time="09:00",
        end_time="10:00",
    )
    stream_east = Stream.objects.create(
        tenant=class_attendance_tenant, school_class=class_a, name="East",
    )
    stream_west = Stream.objects.create(
        tenant=class_attendance_tenant, school_class=class_a, name="West",
    )
    student_east = Student.objects.create(
        tenant=class_attendance_tenant,
        admission_number="ATTN-E1",
        first_name="East",
        last_name="Student",
        date_of_birth=date(2015, 1, 1),
        gender="male",
        school_class=class_a,
        stream=stream_east,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    student_west = Student.objects.create(
        tenant=class_attendance_tenant,
        admission_number="ATTN-W1",
        first_name="West",
        last_name="Student",
        date_of_birth=date(2015, 2, 2),
        gender="female",
        school_class=class_a,
        stream=stream_west,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    return {
        "class_a": class_a,
        "class_b": class_b,
        "stream_east": stream_east,
        "stream_west": stream_west,
        "student_east": student_east,
        "student_west": student_west,
        "teacher_user": class_attendance_teacher.user,
    }


@pytest.mark.django_db
class TestClassAttendance:
    def test_teacher_sees_assigned_classes(self, api_client, class_attendance_setup):
        api_client.force_authenticate(user=class_attendance_setup["teacher_user"])
        response = api_client.get("/api/v1/attendance/class-marking/options/")
        assert response.status_code == 200
        classes = response.data["data"]["classes"]
        assert len(classes) == 2
        assert {row["code"] for row in classes} == {"G5", "G6"}

    def test_class_requires_stream_before_students(self, api_client, class_attendance_setup):
        api_client.force_authenticate(user=class_attendance_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/attendance/class-marking/options/",
            {"school_class": class_attendance_setup["class_a"].id},
        )
        assert response.status_code == 200
        data = response.data["data"]
        assert data["requires_stream"] is True
        assert len(data["streams"]) == 2
        assert data["students"] == []

    def test_stream_filters_students(self, api_client, class_attendance_setup):
        api_client.force_authenticate(user=class_attendance_setup["teacher_user"])
        response = api_client.get(
            "/api/v1/attendance/class-marking/options/",
            {
                "school_class": class_attendance_setup["class_a"].id,
                "stream": class_attendance_setup["stream_east"].id,
                "date": "2026-07-09",
            },
        )
        assert response.status_code == 200
        students = response.data["data"]["students"]
        assert len(students) == 1
        assert students[0]["admission_number"] == "ATTN-E1"

    def test_bulk_save_defaults_present_and_absent(self, api_client, class_attendance_setup):
        api_client.force_authenticate(user=class_attendance_setup["teacher_user"])
        response = api_client.post(
            "/api/v1/attendance/class-marking/bulk/",
            {
                "school_class": str(class_attendance_setup["class_a"].id),
                "stream": str(class_attendance_setup["stream_east"].id),
                "date": "2026-07-09",
                "entries": [
                    {"student": str(class_attendance_setup["student_east"].id), "present": True},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        record = AttendanceRecord.objects.get(
            student=class_attendance_setup["student_east"],
            date=date(2026, 7, 9),
        )
        assert record.status == "present"
        assert record.check_in is not None
        assert record.marked_by_id == class_attendance_setup["teacher_user"].id

    def test_teacher_cannot_mark_unassigned_class(self, api_client, class_attendance_setup, class_attendance_tenant):
        other_teacher = onboard_staff(
            class_attendance_tenant,
            data={
                "first_name": "Other",
                "last_name": "Teacher",
                "email": "other.teacher@test.edu",
                "phone": "+254700000502",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2026-01-01",
            },
        )
        api_client.force_authenticate(user=other_teacher.user)
        response = api_client.get(
            "/api/v1/attendance/class-marking/options/",
            {"school_class": class_attendance_setup["class_a"].id},
        )
        assert response.status_code == 403