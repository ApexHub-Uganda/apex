"""Tenant isolation tests."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.academics.models import AcademicYear, Class
from apps.students.models import Student


@pytest.mark.django_db
class TestTenantIsolation:
    def test_student_queryset_filtered_by_tenant(self, tenant, other_tenant, school_admin):
        Student.objects.create(
            tenant=tenant,
            admission_number="T-001",
            first_name="Alice",
            last_name="One",
            date_of_birth="2010-01-01",
            gender="female",
            enrollment_date="2025-09-01",
        )
        Student.objects.create(
            tenant=other_tenant,
            admission_number="O-001",
            first_name="Bob",
            last_name="Two",
            date_of_birth="2010-02-01",
            gender="male",
            enrollment_date="2025-09-01",
        )

        from apps.tenants.context import TenantContext
        TenantContext.set_user(school_admin)
        TenantContext.set_tenant(tenant)

        visible = Student.objects.all()
        assert visible.count() == 1
        assert visible.first().admission_number == "T-001"

        TenantContext.clear()

    def test_api_returns_only_tenant_students(self, api_client, tenant, other_tenant, school_admin):
        Student.objects.create(
            tenant=tenant,
            admission_number="T-001",
            first_name="Alice",
            last_name="One",
            date_of_birth="2010-01-01",
            gender="female",
            enrollment_date="2025-09-01",
        )
        Student.objects.create(
            tenant=other_tenant,
            admission_number="O-001",
            first_name="Bob",
            last_name="Two",
            date_of_birth="2010-02-01",
            gender="male",
            enrollment_date="2025-09-01",
        )

        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/students/")
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["admission_number"] == "T-001"

    def test_super_admin_can_filter_by_tenant(self, api_client, tenant, other_tenant, super_admin):
        year1 = AcademicYear.objects.create(
            tenant=tenant, name="2025", start_date="2025-01-01", end_date="2025-12-31",
        )
        AcademicYear.objects.create(
            tenant=other_tenant, name="2025", start_date="2025-01-01", end_date="2025-12-31",
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f"/api/v1/academics/years/?tenant_id={tenant.id}")
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert all(str(r.get("tenant")) == str(tenant.id) for r in results)

    def test_cross_tenant_data_not_visible_in_academics(self, api_client, tenant, other_tenant, school_admin):
        AcademicYear.objects.create(
            tenant=other_tenant, name="Other Year", start_date="2025-01-01", end_date="2025-12-31",
        )
        AcademicYear.objects.create(
            tenant=tenant, name="My Year", start_date="2025-01-01", end_date="2025-12-31",
        )

        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/academics/years/")
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["name"] == "My Year"