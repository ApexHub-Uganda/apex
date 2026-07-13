"""School registration validation and junk tenant pruning."""
from __future__ import annotations

import pytest
from django.core.management import call_command
from rest_framework import status

from apps.tenants.models import Tenant
from apps.tenants.school_validation import is_probable_test_or_junk_school


@pytest.mark.django_db
class TestSchoolValidation:
    def test_public_registration_rejects_duplicate_email(self, api_client):
        payload = {
            "name": "Hillside Academy",
            "email": "principal@hillsideacademy.edu",
            "admin_email": "principal@hillsideacademy.edu",
            "admin_password": "TestPass@2026",
            "admin_first_name": "Patricia",
            "admin_last_name": "Mwangi",
        }
        first = api_client.post("/api/v1/tenants/register/", payload, format="json")
        assert first.status_code == status.HTTP_201_CREATED

        second = api_client.post("/api/v1/tenants/register/", payload, format="json")
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(second.json()).lower()

    def test_public_registration_rejects_junk_school(self, api_client):
        response = api_client.post(
            "/api/v1/tenants/register/",
            {
                "name": "T2",
                "email": "t2@t.edu",
                "admin_email": "t2@t.edu",
                "admin_password": "TestPass@2026",
                "admin_first_name": "Test",
                "admin_last_name": "User",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Tenant.objects.filter(name="T2").exists()

    def test_super_admin_create_rejects_reserved_test_code(self, api_client, super_admin):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            "/api/v1/tenants/",
            {
                "name": "Legit Academy",
                "code": "TEST",
                "email": "admin@legitacademy.edu",
                "status": "active",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Tenant.objects.filter(code="TEST", name="Legit Academy").exists()

    def test_probable_test_detector_flags_fixture_school(self):
        assert is_probable_test_or_junk_school(
            name="Test School",
            code="TEST",
            email="school@test.edu",
        )

    def test_prune_test_schools_command(self, db):
        Tenant.objects.create(
            name="T3",
            code="T3",
            email="t3@t.edu",
            status="active",
        )
        Tenant.objects.create(
            name="Real Example School",
            code="REALX",
            email="admin@realexampleschool.edu",
            status="active",
        )

        call_command("prune_test_schools")

        assert not Tenant.objects.filter(code="T3").exists()
        assert Tenant.objects.filter(code="REALX").exists()