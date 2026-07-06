"""Plan deletion with graceful subscription reassignment."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.core.constants import PlanSlug
from apps.subscriptions.models import Plan, Subscription


@pytest.mark.django_db
class TestPlanDelete:
    def test_deletion_preview_lists_reassign_options(self, api_client, super_admin, plan, tenant):
        replacement = Plan.objects.create(
            name="Replacement Plan",
            slug="replacement-plan",
            is_active=True,
        )
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f"/api/v1/subscriptions/plans/manage/{plan.id}/deletion-preview/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["subscription_count"] >= 1
        assert data["requires_reassign"] is True
        assert any(opt["id"] == str(replacement.id) for opt in data["reassign_options"])
        assert any(school["school"] == tenant.name for school in data["schools"])

    def test_delete_requires_reassign_when_subscriptions_exist(self, api_client, super_admin, plan, tenant):
        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(f"/api/v1/subscriptions/plans/manage/{plan.id}/")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "reassign_required"
        assert Plan.objects.filter(pk=plan.id).exists()

    def test_delete_with_reassign_moves_subscriptions(self, api_client, super_admin, plan, tenant):
        replacement = Plan.objects.create(
            name="Replacement Plan",
            slug="replacement-plan",
            is_active=True,
        )
        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(
            f"/api/v1/subscriptions/plans/manage/{plan.id}/",
            {"reassign_to": str(replacement.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "moved" in response.data["message"].lower()
        assert not Plan.objects.filter(pk=plan.id).exists()
        assert Subscription.objects.filter(tenant=tenant, plan=replacement).exists()
        assert not Subscription.objects.filter(plan=plan).exists()

    def test_can_delete_unused_plan(self, api_client, super_admin, db):
        unused = Plan.objects.create(
            name="Unused Plan",
            slug="unused-plan-delete",
            is_active=True,
        )
        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(f"/api/v1/subscriptions/plans/manage/{unused.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert not Plan.objects.filter(pk=unused.id).exists()

    def test_cannot_reassign_to_same_plan(self, api_client, super_admin, plan, tenant):
        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(
            f"/api/v1/subscriptions/plans/manage/{plan.id}/",
            {"reassign_to": str(plan.id)},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "invalid_reassign_target"
        assert Plan.objects.filter(pk=plan.id).exists()