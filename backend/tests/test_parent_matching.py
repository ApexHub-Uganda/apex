"""Parent–learner matching API tests."""
from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.students.models import Parent, Student
from apps.subscriptions.services import assign_plan_features


def unwrap(response):
    data = response.data
    return data.get("data", data) if isinstance(data, dict) else data


@pytest.fixture
def parent_matching_setup(db, tenant, plan, school_admin):
    assign_plan_features(plan, ["student_management", "parent_management"])
    client = APIClient()
    client.force_authenticate(user=school_admin)
    parent = Parent.objects.create(
        tenant=tenant,
        first_name="Jane",
        last_name="Okello",
        email="jane@example.com",
        phone="+256700000001",
    )
    student = Student.objects.create(
        tenant=tenant,
        admission_number="ADM-001",
        first_name="Peter",
        last_name="Okello",
        date_of_birth="2015-03-10",
        gender="male",
        enrollment_date=timezone.now().date(),
    )
    return client, parent, student


@pytest.mark.django_db
def test_link_and_unlink_student(parent_matching_setup):
    client, parent, student = parent_matching_setup
    link = client.post(
        f"/api/v1/students/parents/{parent.id}/link-student/",
        {"student_id": str(student.id)},
        format="json",
    )
    assert link.status_code == 200
    children = unwrap(link).get("children", [])
    assert any(str(c["id"]) == str(student.id) for c in children)

    summary = client.get("/api/v1/students/parents/matching-summary/")
    assert summary.status_code == 200
    assert unwrap(summary)["linked_pairs"] >= 1

    unlink = client.post(
        f"/api/v1/students/parents/{parent.id}/unlink-student/",
        {"student_id": str(student.id)},
        format="json",
    )
    assert unlink.status_code == 200
    assert unwrap(unlink).get("children", []) == []