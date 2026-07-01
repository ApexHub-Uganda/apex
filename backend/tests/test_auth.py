"""Authentication tests."""
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import LoginHistory


@pytest.mark.django_db
class TestAuthentication:
    def test_login_success(self, api_client, school_admin):
        response = api_client.post("/api/v1/auth/login/", {
            "email": "admin@test.edu",
            "password": "TestPass@2026",
        })
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == "admin@test.edu"
        assert LoginHistory.objects.filter(email="admin@test.edu", success=True).exists()

    def test_login_invalid_credentials(self, api_client, school_admin):
        response = api_client.post("/api/v1/auth/login/", {
            "email": "admin@test.edu",
            "password": "wrongpassword",
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert LoginHistory.objects.filter(email="admin@test.edu", success=False).exists()

    def test_me_endpoint(self, api_client, school_admin):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == school_admin.email

    def test_logout(self, api_client, school_admin):
        login_resp = api_client.post("/api/v1/auth/login/", {
            "email": "admin@test.edu",
            "password": "TestPass@2026",
        })
        refresh = login_resp.data["refresh"]
        api_client.force_authenticate(user=school_admin)
        response = api_client.post("/api/v1/auth/logout/", {"refresh": refresh})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_super_admin_login(self, api_client, super_admin):
        response = api_client.post("/api/v1/auth/login/", {
            "email": "super@test.io",
            "password": "TestPass@2026",
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["role"] == "super_admin"