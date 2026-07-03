"""Tests for HR staff onboarding."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.staff.models import Staff, Teacher
from apps.staff.services import StaffOnboardingError, onboard_staff


@pytest.mark.django_db
class TestStaffOnboarding:
    def test_onboard_teacher_creates_user_and_teacher_profile(self, tenant, school_admin):
        staff = onboard_staff(
            tenant,
            actor=school_admin,
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@test.edu",
                "phone": "+254700000001",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2025-01-15",
                "has_portal_access": True,
            },
        )
        assert staff.user_id is not None
        assert staff.user.role == UserRole.TEACHER
        assert staff.user.email == "jane.doe@test.edu"
        assert hasattr(staff, "teacher_profile")
        assert staff.employee_id.startswith(tenant.code)

    def test_onboard_bursar_no_teacher_profile(self, tenant, school_admin):
        staff = onboard_staff(
            tenant,
            actor=school_admin,
            data={
                "first_name": "Sam",
                "last_name": "Finance",
                "email": "bursar@test.edu",
                "phone": "+254700000002",
                "portal_role": UserRole.BURSAR,
                "date_joined": "2025-02-01",
            },
        )
        assert staff.portal_role == UserRole.BURSAR
        assert staff.staff_category == "finance"
        assert not Teacher.objects.filter(staff=staff).exists()

    def test_duplicate_email_rejected(self, tenant, school_admin):
        onboard_staff(
            tenant,
            actor=school_admin,
            data={
                "first_name": "A",
                "last_name": "One",
                "email": "dup@test.edu",
                "phone": "1",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2025-01-01",
            },
        )
        with pytest.raises(StaffOnboardingError):
            onboard_staff(
                tenant,
                actor=school_admin,
                data={
                    "first_name": "B",
                    "last_name": "Two",
                    "email": "dup@test.edu",
                    "phone": "2",
                    "portal_role": UserRole.LIBRARIAN,
                    "date_joined": "2025-01-01",
                },
            )

    def test_api_create_staff(self, tenant, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post("/api/v1/staff/", {
            "first_name": "API",
            "last_name": "Staff",
            "email": "api.staff@test.edu",
            "phone": "+254711111111",
            "portal_role": UserRole.HR_MANAGER,
            "designation": "HR Manager",
            "date_joined": "2025-03-01",
            "has_portal_access": True,
        }, format="json")
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["portal_role"] == UserRole.HR_MANAGER
        assert Staff.objects.filter(email="api.staff@test.edu").exists()

    def test_role_options_endpoint(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.get("/api/v1/staff/role-options/")
        assert response.status_code == 200
        roles = response.json()["data"]
        assert any(r["role"] == UserRole.TEACHER for r in roles)