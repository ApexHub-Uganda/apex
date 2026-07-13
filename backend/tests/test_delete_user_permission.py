"""Delete User permission gates directory record removal."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework import status

from apps.academics.models import AcademicYear, Class, Subject, TeachingAssignment
from apps.core.constants import UserRole
from apps.students.models import Parent, Student
from apps.staff.models import Staff, Teacher
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_permissions import save_role_permissions


@pytest.fixture
def delete_user_plan(db, plan):
    assign_plan_features(plan, [
        "student_management", "parent_management", "staff_management", "delete_user",
    ])
    return plan


def _grant_delete_user(tenant, *, can_read: bool, can_write: bool) -> None:
    save_role_permissions(tenant, [
        {
            "role": UserRole.TEACHER,
            "module_key": "core_management",
            "can_read": can_read,
            "can_write": can_write,
        },
        {
            "role": UserRole.TEACHER,
            "feature_key": "delete_user",
            "can_read": can_read,
            "can_write": can_write,
        },
        {
            "role": UserRole.TEACHER,
            "feature_key": "student_management",
            "can_read": True,
            "can_write": True,
        },
        {
            "role": UserRole.TEACHER,
            "feature_key": "parent_management",
            "can_read": True,
            "can_write": True,
        },
        {
            "role": UserRole.TEACHER,
            "feature_key": "staff_management",
            "can_read": True,
            "can_write": True,
        },
    ])


def _setup_teacher_student_scope(tenant, teacher_user):
    """Give the teacher academic visibility to the student under test."""
    staff = Staff.objects.create(
        tenant=tenant,
        user=teacher_user,
        employee_id="T-DEL-SCOPE",
        first_name=teacher_user.first_name,
        last_name=teacher_user.last_name,
        email=teacher_user.email,
        phone="+254700000099",
        date_joined="2025-01-01",
        portal_role=UserRole.TEACHER,
        staff_category="teaching",
        employment_type="full_time",
        status="active",
    )
    teacher = Teacher.objects.create(tenant=tenant, staff=staff)
    year = AcademicYear.objects.create(
        tenant=tenant,
        name="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=tenant,
        name="Grade 1",
        code="G1-DEL",
        academic_year=year,
    )
    subject = Subject.objects.create(tenant=tenant, name="Mathematics", code="MTH-DEL")
    TeachingAssignment.objects.create(
        tenant=tenant,
        teacher=teacher,
        school_class=school_class,
        subject=subject,
        academic_year=year,
        is_active=True,
    )
    return school_class


@pytest.mark.django_db
class TestDeleteUserPermission:
    def test_student_delete_requires_delete_user_write(
        self, api_client, tenant, delete_user_plan, teacher_user,
    ):
        school_class = _setup_teacher_student_scope(tenant, teacher_user)
        student = Student.objects.create(
            tenant=tenant,
            admission_number="DEL-001",
            first_name="Delete",
            last_name="Me",
            date_of_birth="2010-01-01",
            gender="male",
            enrollment_date="2025-09-01",
            school_class=school_class,
        )

        _grant_delete_user(tenant, can_read=True, can_write=False)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/students/{student.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Student.objects.filter(pk=student.id, is_deleted=False).exists()

        _grant_delete_user(tenant, can_read=True, can_write=True)
        response = api_client.delete(f"/api/v1/students/{student.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        student.refresh_from_db()
        assert student.is_deleted is True

    def test_parent_delete_requires_delete_user_write(
        self, api_client, tenant, delete_user_plan, teacher_user,
    ):
        parent = Parent.objects.create(
            tenant=tenant,
            first_name="Guardian",
            last_name="Remove",
            email="guardian.remove@realschool.edu",
            phone="+254700000001",
        )

        _grant_delete_user(tenant, can_read=True, can_write=False)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/students/parents/{parent.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        _grant_delete_user(tenant, can_read=True, can_write=True)
        response = api_client.delete(f"/api/v1/students/parents/{parent.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        parent.refresh_from_db()
        assert parent.is_deleted is True

    def test_staff_delete_requires_delete_user_write(
        self, api_client, tenant, delete_user_plan, teacher_user,
    ):
        staff = Staff.objects.create(
            tenant=tenant,
            employee_id="DEL-STF-1",
            first_name="Staff",
            last_name="Remove",
            email="staff.remove@realschool.edu",
            phone="+254700000002",
            date_joined="2025-01-01",
            portal_role=UserRole.TEACHER,
            staff_category="teaching",
            employment_type="full_time",
            status="active",
        )

        _grant_delete_user(tenant, can_read=True, can_write=False)
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f"/api/v1/staff/{staff.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        _grant_delete_user(tenant, can_read=True, can_write=True)
        response = api_client.delete(f"/api/v1/staff/{staff.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        staff.refresh_from_db()
        assert staff.is_deleted is True

    def test_school_admin_can_delete_without_explicit_grant(
        self, api_client, tenant, delete_user_plan, school_admin,
    ):
        student = Student.objects.create(
            tenant=tenant,
            admission_number="ADM-DEL",
            first_name="Admin",
            last_name="Delete",
            date_of_birth="2010-05-01",
            gender="female",
            enrollment_date="2025-09-01",
        )
        api_client.force_authenticate(user=school_admin)
        response = api_client.delete(f"/api/v1/students/{student.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT