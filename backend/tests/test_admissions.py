"""Admission applications, vacancies, and public listing tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admissions.models import AdmissionApplication, AdmissionVacancy
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def admissions_plan(plan):
    assign_plan_features(plan, [
        "admissions", "admitted_students", "admission_vacancies", "classes",
    ])
    return plan


@pytest.mark.django_db
class TestAdmissionApplications:
    def test_create_application_without_student(self, api_client, school_admin, admissions_plan):
        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/admissions/applications/",
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "date_of_birth": "2015-03-10",
                "gender": "female",
                "parent_name": "John Doe",
                "parent_phone": "+254700000001",
                "grade_applied": "Grade 4",
                "application_date": "2026-01-15",
                "status": "pending",
            },
            format="json",
        )
        assert response.status_code == 201
        assert AdmissionApplication.objects.filter(last_name="Doe").exists()

    def test_admit_creates_student(self, api_client, school_admin, admissions_plan, tenant):
        api_client.force_authenticate(user=school_admin)
        application = AdmissionApplication.objects.create(
            tenant=tenant,
            first_name="Sam",
            last_name="Otieno",
            date_of_birth="2014-06-01",
            gender="male",
            parent_name="Mary Otieno",
            parent_phone="+254700000002",
            grade_applied="Grade 5",
            application_date=timezone.now().date(),
            status="approved",
        )
        response = api_client.post(f"/api/v1/admissions/applications/{application.id}/admit/", {}, format="json")
        assert response.status_code == 200
        application.refresh_from_db()
        assert application.status == "admitted"
        assert application.student_id is not None
        assert Student.objects.filter(pk=application.student_id).exists()

    def test_admitted_list_endpoint(self, api_client, school_admin, admissions_plan, tenant):
        api_client.force_authenticate(user=school_admin)
        AdmissionApplication.objects.create(
            tenant=tenant,
            first_name="Ad",
            last_name="Mitted",
            date_of_birth="2013-01-01",
            gender="male",
            parent_name="Parent",
            parent_phone="+254700000003",
            grade_applied="Grade 6",
            application_date=timezone.now().date(),
            status="admitted",
        )
        response = api_client.get("/api/v1/admissions/admitted/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        if isinstance(results, dict):
            results = results.get("results", [])
        assert len(results) >= 1


@pytest.mark.django_db
class TestAdmissionVacancies:
    def test_create_and_publish_vacancy(self, api_client, school_admin, admissions_plan):
        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/admissions/vacancies/",
            {
                "title": "Grade 1 Intake 2026",
                "description": "Day scholar openings",
                "grade_levels": "Grade 1",
                "openings_count": 5,
                "show_on_landing": True,
                "show_on_parent_portal": True,
            },
            format="json",
        )
        assert response.status_code == 201
        vacancy_id = response.data["id"]
        publish = api_client.post(f"/api/v1/admissions/vacancies/{vacancy_id}/publish/", {}, format="json")
        assert publish.status_code == 200
        assert AdmissionVacancy.objects.get(pk=vacancy_id).is_published is True

    def test_public_vacancies_list(self, api_client, school_admin, admissions_plan, tenant):
        api_client.force_authenticate(user=school_admin)
        deadline = (timezone.now() + timedelta(days=30)).date()
        vacancy = AdmissionVacancy.objects.create(
            tenant=tenant,
            title="Public Opening",
            grade_levels="Grade 2",
            openings_count=3,
            is_active=True,
            is_published=True,
            show_on_landing=True,
            application_deadline=deadline,
        )
        api_client.force_authenticate(user=None)
        response = api_client.get("/api/v1/admissions/public/vacancies/")
        assert response.status_code == 200
        vacancies = response.data["data"]["vacancies"]
        assert any(v["id"] == str(vacancy.id) for v in vacancies)