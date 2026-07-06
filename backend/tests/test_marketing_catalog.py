"""Public marketing catalog for landing page."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.subscriptions.services import assign_plan_features
from apps.subscriptions.seed_features import seed_feature_catalog


@pytest.mark.django_db
class TestMarketingCatalog:
    def test_public_marketing_endpoint(self, plan):
        seed_feature_catalog()
        assign_plan_features(plan, ["student_management", "classes", "staff_management"])
        plan.is_public = True
        plan.save()

        client = APIClient()
        response = client.get("/api/v1/subscriptions/marketing/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["plans"]) >= 1
        assert data["plans"][0]["monthly"] == float(plan.price_monthly)
        assert len(data["features"]) >= 1
        assert len(data["stats"]) == 5
        assert "comparison" in data

    def test_trusted_schools_endpoint(self, tenant, other_tenant):
        client = APIClient()
        response = client.get("/api/v1/subscriptions/marketing/trusted-schools/")
        assert response.status_code == 200
        schools = response.json()["data"]["schools"]
        assert len(schools) == 2
        names = {s["name"] for s in schools}
        assert names == {"Test School", "Other School"}
        assert all("id" in s for s in schools)

    def test_trusted_schools_respects_limit(self, tenant, other_tenant):
        client = APIClient()
        response = client.get("/api/v1/subscriptions/marketing/trusted-schools/?limit=1")
        assert response.status_code == 200
        assert len(response.json()["data"]["schools"]) == 1