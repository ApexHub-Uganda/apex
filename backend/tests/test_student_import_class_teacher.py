"""Class teacher defaults for student bulk import."""
from __future__ import annotations

import io
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Stream
from apps.core.bulk_import import generate_import_template
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.students.import_handlers import STUDENT_IMPORT_SPEC, get_student_import_context
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def teacher_import_plan(db, plan):
    assign_plan_features(plan, [
        "student_management", "classes", "academic_years", "class_teacher_tools",
    ])
    return plan


@pytest.fixture
def class_teacher_setup(db, tenant, teacher_import_plan, monkeypatch):
    class _EmailResult:
        success = True
        message = ""

    monkeypatch.setattr(
        "apps.staff.portal_credentials.EmailService.send",
        lambda *args, **kwargs: _EmailResult(),
    )
    year = AcademicYear.objects.create(
        tenant=tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    teacher_staff = onboard_staff(
        tenant,
        data={
            "first_name": "Class",
            "last_name": "Teacher",
            "email": "class.teacher.import@test.edu",
            "phone": "+254700000601",
            "portal_role": UserRole.CLASS_TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    school_class = Class.objects.create(
        tenant=tenant,
        name="Grade 4",
        code="G4",
        academic_year=year,
        class_teacher=teacher_staff.teacher_profile,
    )
    stream = Stream.objects.create(tenant=tenant, school_class=school_class, name="North")
    return {
        "user": teacher_staff.user,
        "school_class": school_class,
        "stream": stream,
    }


@pytest.mark.django_db
def test_class_teacher_gets_default_class(class_teacher_setup):
    context = get_student_import_context(class_teacher_setup["user"])
    assert context["is_class_teacher"] is True
    assert context["default_class_id"] == str(class_teacher_setup["school_class"].id)
    assert context["default_stream_id"] == str(class_teacher_setup["stream"].id)
    assert len(context["classes"]) == 1
    assert context["can_enroll_students"] is True
    assert context["classes"][0]["can_enroll"] is True


@pytest.mark.django_db
def test_class_teacher_can_validate_and_commit_import(class_teacher_setup):
    user = class_teacher_setup["user"]
    school_class = class_teacher_setup["school_class"]
    stream = class_teacher_setup["stream"]
    client = APIClient()
    client.force_authenticate(user=user)

    csv_content = (
        "First Name,Last Name,Sex\n"
        "Alice,Okello,F\n"
    )
    upload = io.BytesIO(csv_content.encode("utf-8"))
    upload.name = "students.csv"
    validate_response = client.post(
        "/api/v1/students/validate-import/",
        {
            "file": upload,
            "school_class": str(school_class.id),
            "stream": str(stream.id),
        },
        format="multipart",
    )
    assert validate_response.status_code == 200, validate_response.content
    payload = validate_response.json()["data"]
    assert payload["valid_count"] == 1
    assert payload["can_commit"] is True

    commit_response = client.post(
        "/api/v1/students/commit-import/",
        {
            "rows": payload["ready"],
            "school_class": str(school_class.id),
            "stream": str(stream.id),
        },
        format="json",
    )
    assert commit_response.status_code == 200, commit_response.content
    assert commit_response.json()["data"]["created"] == 1


@pytest.mark.django_db
def test_class_teacher_import_context_endpoint(class_teacher_setup):
    client = APIClient()
    client.force_authenticate(user=class_teacher_setup["user"])
    response = client.get("/api/v1/students/import-context/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["can_enroll_students"] is True
    assert data["can_enroll_in_default_class"] is True


@pytest.mark.django_db
def test_class_teacher_excel_template_download(class_teacher_setup):
    client = APIClient()
    client.force_authenticate(user=class_teacher_setup["user"])
    response = client.get("/api/v1/students/import-template/")
    assert response.status_code == 200
    content, _, _ = generate_import_template(STUDENT_IMPORT_SPEC)
    assert response.content[:2] == b"PK"
    assert len(content) > 0