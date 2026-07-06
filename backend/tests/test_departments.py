"""Department CRUD and feature-gate tests."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.academics.models import Department
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def departments_plan(plan):
    assign_plan_features(plan, ["departments", "staff_management"])
    return plan


@pytest.mark.django_db
class TestDepartments:
    def test_list_requires_feature(self, api_client, school_admin, tenant):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/academics/departments/")
        assert response.status_code in (403, 402)

    def test_create_department_with_core_feature(self, api_client, school_admin, departments_plan):
        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/academics/departments/",
            {
                "name": "Sciences",
                "code": "SCI",
                "description": "Science department",
            },
            format="json",
        )
        assert response.status_code == 201
        assert Department.objects.filter(code="SCI").exists()

    def test_hr_departments_feature_also_grants_access(self, api_client, school_admin, plan, tenant):
        assign_plan_features(plan, ["hr_departments"])
        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/academics/departments/",
            {"name": "Administration", "code": "ADMIN"},
            format="json",
        )
        assert response.status_code == 201