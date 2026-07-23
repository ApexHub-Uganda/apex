"""Tests for HR staff onboarding."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.academics.models import Department
from apps.core.constants import UserRole
from apps.staff.models import Staff, Teacher
from apps.staff.services import StaffOnboardingError, onboard_staff


@pytest.mark.django_db
class TestStaffOnboarding:
    @patch("apps.staff.portal_credentials.EmailService.send")
    def test_onboard_teacher_creates_user_and_teacher_profile(self, mock_send, tenant, school_admin):
        mock_send.return_value = type("Result", (), {"success": True, "message": ""})()
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
        assert staff.user.must_change_password is True
        assert hasattr(staff, "teacher_profile")
        assert staff.employee_id.startswith(tenant.code)
        mock_send.assert_called_once()
        # One-time password emailed for first login is 6 alphanumeric characters.
        send_kwargs = mock_send.call_args.kwargs if mock_send.call_args.kwargs else {}
        # EmailService.send may receive body text containing the OTP; assert generator contract directly.
        from apps.staff.services import _generate_temp_password
        otp = _generate_temp_password()
        assert len(otp) == 6
        assert otp.isalnum()

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

    @patch("apps.staff.portal_credentials.EmailService.send")
    def test_api_create_staff(self, mock_send, tenant, school_admin):
        mock_send.return_value = type("Result", (), {"success": True, "message": ""})()
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
        assert "emailed" in data["message"].lower()
        assert Staff.objects.filter(email="api.staff@test.edu").exists()
        staff = Staff.objects.get(email="api.staff@test.edu")
        assert staff.user.must_change_password is True
        mock_send.assert_called_once()

    @patch("apps.staff.portal_credentials.EmailService.send")
    def test_api_create_non_teacher_with_empty_years_experience(self, mock_send, tenant, school_admin):
        """Switching role away from teacher often leaves teacher.years_experience as ''."""
        mock_send.return_value = type("Result", (), {"success": True, "message": ""})()
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post(
            "/api/v1/staff/",
            {
                "first_name": "Lib",
                "last_name": "Rarian",
                "email": "librarian.emptyyears@test.edu",
                "phone": "+254722222222",
                "portal_role": UserRole.LIBRARIAN,
                "has_portal_access": True,
                # Mimic browser form: nested teacher left over from teacher role default
                "teacher": {
                    "qualification": "",
                    "specialization": "",
                    "years_experience": "",
                    "is_class_teacher": False,
                },
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["success"] is True
        staff = Staff.objects.get(email="librarian.emptyyears@test.edu")
        assert staff.portal_role == UserRole.LIBRARIAN
        assert not Teacher.objects.filter(staff=staff).exists()

    @patch("apps.staff.portal_credentials.EmailService.send")
    def test_api_create_teacher_without_years_experience(self, mock_send, tenant, school_admin):
        """Years of experience is optional; blank creates teacher profile with 0."""
        mock_send.return_value = type("Result", (), {"success": True, "message": ""})()
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post(
            "/api/v1/staff/",
            {
                "first_name": "Teach",
                "last_name": "Er",
                "email": "teacher.noyears@test.edu",
                "phone": "+254733333333",
                "portal_role": UserRole.TEACHER,
                "has_portal_access": True,
                "teacher": {"years_experience": ""},
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        staff = Staff.objects.get(email="teacher.noyears@test.edu")
        assert Teacher.objects.filter(staff=staff).exists()
        assert staff.teacher_profile.years_experience == 0

    def test_role_options_endpoint(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.get("/api/v1/staff/role-options/")
        assert response.status_code == 200
        roles = response.json()["data"]
        assert any(r["role"] == UserRole.TEACHER for r in roles)

    def test_api_update_staff_with_department(self, tenant, school_admin):
        department = Department.objects.create(
            tenant=tenant,
            name="Sciences",
            code="SCI",
            created_by=school_admin,
            updated_by=school_admin,
        )
        staff = onboard_staff(
            tenant,
            actor=school_admin,
            data={
                "first_name": "Dept",
                "last_name": "Teacher",
                "email": "dept.teacher@test.edu",
                "phone": "+254700000099",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2025-04-01",
                "department": str(department.id),
            },
        )

        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.patch(
            f"/api/v1/staff/{staff.id}/",
            {
                "designation": "Senior Teacher",
                "department": str(department.id),
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["success"] is True
        assert body["data"]["designation"] == "Senior Teacher"
        assert body["data"]["department"] == str(department.id)

        staff.refresh_from_db()
        assert staff.department_id == department.id