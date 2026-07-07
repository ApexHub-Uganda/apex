"""School suspension enforcement for school-admin access."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.communication.models import Notification
from apps.tenants.models import Tenant


@pytest.mark.django_db
class TestTenantSuspension:
    def test_context_payload_blocks_modules_when_suspended(self, api_client, school_admin, tenant):
        tenant.suspend(reason="Policy review")
        api_client.force_authenticate(user=school_admin)

        response = api_client.get("/api/v1/tenants/context/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["is_suspended"] is True
        assert data["access_blocked"] is True
        assert data["module_menu"] == []
        assert data["enabled_feature_keys"] == []
        assert data["suspension_reason"] == "Policy review"

    def test_school_dashboard_blocked_when_suspended(self, api_client, school_admin, tenant):
        tenant.suspend(reason="Non-payment")
        api_client.force_authenticate(user=school_admin)

        response = api_client.get("/api/v1/analytics/dashboard/school/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"]["code"] == "tenant_suspended"

    def test_school_admin_can_still_read_profile_when_suspended(self, api_client, school_admin, tenant):
        tenant.suspend()
        api_client.force_authenticate(user=school_admin)

        response = api_client.get("/api/v1/auth/me/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.data.get("data", response.data)
        assert payload["tenant_is_suspended"] is True

    def test_unsuspend_restores_dashboard_access(self, api_client, school_admin, tenant):
        tenant.suspend()
        tenant.unsuspend()
        api_client.force_authenticate(user=school_admin)

        response = api_client.get("/api/v1/analytics/dashboard/school/")

        assert response.status_code == status.HTTP_200_OK