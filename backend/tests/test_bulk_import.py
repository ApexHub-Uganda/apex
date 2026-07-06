"""Tests for CSV bulk import infrastructure."""
from __future__ import annotations

import io

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class
from apps.core.bulk_import import generate_csv_template, parse_upload, validate_rows
from apps.students.import_handlers import (
    STUDENT_IMPORT_SPEC,
    commit_parent_rows,
    student_import_resolver,
)
from apps.students.models import Parent, Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def import_plan(plan):
    assign_plan_features(plan, [
        "student_management", "parent_management", "staff_management",
        "classes", "academic_years", "terms", "student_billing",
    ])
    return plan


@pytest.fixture
def academic_setup(db, tenant):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    school_class = Class.objects.create(
        tenant=tenant, name="Grade 7", code="G7A", academic_year=year, capacity=40,
    )
    return year, school_class


def test_generate_csv_template_has_headers():
    content = generate_csv_template(STUDENT_IMPORT_SPEC).decode("utf-8-sig")
    assert "Admission Number" in content
    assert "Class Code" in content
    assert "UPI" not in content
    assert content.count("\n") <= 3  # header + hint row only


def test_parent_template_is_minimal():
    from apps.students.import_handlers import PARENT_IMPORT_SPEC

    content = generate_csv_template(PARENT_IMPORT_SPEC).decode("utf-8-sig")
    assert "M-Pesa" not in content
    assert "First Name" in content
    assert "Email" in content


def test_validate_headers_missing_required():
    headers, rows = parse_upload(io.BytesIO(b"first_name,last_name\nJohn,Doe\n"))
    result = validate_rows(STUDENT_IMPORT_SPEC, headers, rows)
    assert result["can_commit"] is False
    assert any(e["field"] == "admission_number" for e in result["errors"])


@pytest.mark.django_db
def test_student_import_resolver_duplicate_admission(tenant, school_admin, academic_setup):
    _, school_class = academic_setup
    Student.objects.create(
        tenant=tenant,
        admission_number="ADM001",
        first_name="Existing",
        last_name="Student",
        date_of_birth="2010-01-01",
        gender="male",
        enrollment_date="2026-01-15",
        school_class=school_class,
        created_by=school_admin,
        updated_by=school_admin,
    )
    row = {
        "admission_number": "ADM001",
        "first_name": "New",
        "last_name": "Student",
        "date_of_birth": "2011-02-02",
        "gender": "female",
        "enrollment_date": "2026-01-20",
        "class_code": "G7A",
    }
    errors = student_import_resolver(tenant)(row, 2)
    assert any("already exists" in e["message"] for e in errors)


@pytest.mark.django_db
def test_commit_parent_rows(tenant, school_admin):
    rows = [{
        "first_name": "Jane",
        "last_name": "Wanjiku",
        "email": "jane@example.com",
        "phone": "0712345678",
    }]
    result = commit_parent_rows(tenant, rows, actor=school_admin)
    assert result["created"] == 1
    assert Parent.objects.filter(tenant=tenant, email="jane@example.com").exists()


@pytest.mark.django_db
def test_parent_import_template_endpoint(school_admin, import_plan):
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.get("/api/v1/students/parents/import-template/")
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]
    assert b"First Name" in response.content


@pytest.mark.django_db
def test_student_validate_import_endpoint(school_admin, import_plan, academic_setup):
    client = APIClient()
    client.force_authenticate(user=school_admin)
    csv_content = (
        "Admission Number,First Name,Last Name,Date of Birth,Gender,Class Code\n"
        "ADM100,Peter,Kamau,2012-05-10,male,G7A\n"
    )
    upload = io.BytesIO(csv_content.encode("utf-8"))
    upload.name = "students.csv"
    response = client.post(
        "/api/v1/students/validate-import/",
        {"file": upload},
        format="multipart",
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid_count"] == 1
    assert data["can_commit"] is True