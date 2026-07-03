"""Maintenance mode access control tests."""
from __future__ import annotations

import json

import pytest
from django.conf import settings
from rest_framework import status

from apps.platform.services.maintenance import set_maintenance_mode


@pytest.fixture
def maintenance_on():
    previous = settings.MAINTENANCE_MODE
    set_maintenance_mode(True)
    yield
    set_maintenance_mode(previous)


def _login(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "TestPass@2026"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


@pytest.mark.django_db
class TestMaintenanceMode:
    def test_super_admin_can_access_settings(self, api_client, super_admin, maintenance_on):
        _login(api_client, super_admin)
        response = api_client.get("/api/v1/platform/settings/general/")
        assert response.status_code == status.HTTP_200_OK

    def test_school_admin_blocked_during_maintenance(self, api_client, school_admin):
        _login(api_client, school_admin)
        set_maintenance_mode(True)
        try:
            response = api_client.get("/api/v1/tenants/context/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            payload = json.loads(response.content)
            assert payload["error"]["code"] == "maintenance_mode"
        finally:
            set_maintenance_mode(False)

    def test_school_admin_login_blocked(self, api_client, school_admin, maintenance_on):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": school_admin.email, "password": "TestPass@2026"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "maintenance_mode"
        assert response.data["error"]["message"] == (
            "Apex Hub is currently under maintenance. Please try again later."
        )
        assert "ErrorDetail" not in response.data["error"]["message"]

    def test_super_admin_login_allowed(self, api_client, super_admin, maintenance_on):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": super_admin.email, "password": "TestPass@2026"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_super_admin_can_disable_maintenance(self, api_client, super_admin, maintenance_on):
        _login(api_client, super_admin)
        response = api_client.patch(
            "/api/v1/platform/settings/general/",
            {"maintenance_mode": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["maintenance_mode"] is False

    def test_health_check_stays_public(self, api_client, maintenance_on):
        response = api_client.get("/api/v1/platform/health/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)
        assert "maintenance_mode" in response.data