"""Profile self-service and staff admin edit tests."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.staff.services import onboard_staff


@pytest.fixture
def hr_staff(db, tenant):
    from apps.staff.services import onboard_staff

    return onboard_staff(
        tenant,
        data={
            "first_name": "HR",
            "last_name": "Staff",
            "email": "hr.staff@test.edu",
            "phone": "+254700000099",
            "portal_role": UserRole.HR_MANAGER,
            "date_joined": "2025-01-01",
        },
    )


@pytest.mark.django_db
class TestProfileWorkspace:
    def test_staff_self_profile_update_allowed_fields(self, tenant, hr_staff):
        user = hr_staff.user
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch("/api/v1/auth/me/", {
            "phone": "+254711122233",
            "staff_profile": {
                "personal_email": "personal@test.edu",
                "address": "123 School Road",
                "emergency_contact": "Jane Doe",
                "emergency_phone": "+254700000000",
            },
        }, format="json")

        assert response.status_code == 200
        hr_staff.refresh_from_db()
        assert hr_staff.personal_email == "personal@test.edu"
        assert hr_staff.address == "123 School Road"

    def test_staff_cannot_change_portal_role_via_profile(self, tenant, hr_staff):
        client = APIClient()
        client.force_authenticate(user=hr_staff.user)

        response = client.patch("/api/v1/auth/me/", {
            "role": UserRole.SCHOOL_ADMIN,
            "staff_profile": {"portal_role": UserRole.SCHOOL_ADMIN},
        }, format="json")

        assert response.status_code == 400

    def test_school_admin_updates_staff_profile(self, tenant, school_admin, hr_staff):
        client = APIClient()
        client.force_authenticate(user=school_admin)

        response = client.patch(f"/api/v1/staff/{hr_staff.id}/", {
            "designation": "Senior HR Manager",
            "portal_role": UserRole.HR_MANAGER,
            "notes": "Promoted after review.",
        }, format="json")

        assert response.status_code == 200
        hr_staff.refresh_from_db()
        assert hr_staff.designation == "Senior HR Manager"
        assert hr_staff.notes == "Promoted after review."

    def test_profile_completion_in_me_response(self, tenant, hr_staff):
        client = APIClient()
        client.force_authenticate(user=hr_staff.user)

        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "profile_completion" in data
        assert "editable_fields" in data
        assert "admin_only_fields" in data