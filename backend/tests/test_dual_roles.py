"""Dual portal roles — grant extra roles and switch active role."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.dual_roles import grant_roles, list_user_roles, switch_role
from apps.accounts.models import User, UserRoleAssignment
from apps.core.constants import UserRole


@pytest.mark.django_db
class TestDualRoles:
    def test_grant_and_switch(self, tenant, school_admin):
        teacher = User.objects.create_user(
            email="dual.teacher@test.edu",
            password="TestPass123!",
            first_name="Dual",
            last_name="Teacher",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        result = grant_roles(
            user=teacher,
            roles=[UserRole.PARENT],
            actor=school_admin,
        )
        assert UserRole.PARENT in result["added_roles"]
        assert UserRole.TEACHER in list_user_roles(teacher)
        assert UserRole.PARENT in list_user_roles(teacher)
        assert result["credentials_reused"] is True

        switch_role(user=teacher, role=UserRole.PARENT)
        teacher.refresh_from_db()
        assert teacher.role == UserRole.PARENT
        assert hasattr(teacher, "parent_profile")
        assert teacher.parent_profile is not None

        switch_role(user=teacher, role=UserRole.TEACHER)
        teacher.refresh_from_db()
        assert teacher.role == UserRole.TEACHER

    def test_switch_api(self, tenant, school_admin):
        teacher = User.objects.create_user(
            email="dual.api@test.edu",
            password="TestPass123!",
            first_name="Api",
            last_name="Dual",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=teacher, roles=[UserRole.PARENT], actor=school_admin)

        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.post("/api/v1/auth/switch-role/", {"role": UserRole.PARENT}, format="json")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["success"] is True
        assert body["data"]["access"]
        assert body["data"]["user"]["role"] == UserRole.PARENT
        assert body["data"]["user"]["can_switch_role"] is True
        assert UserRole.TEACHER in body["data"]["user"]["available_roles"]

    def test_admin_grant_api(self, tenant, school_admin):
        teacher = User.objects.create_user(
            email="dual.grant@test.edu",
            password="TestPass123!",
            first_name="Grant",
            last_name="Me",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post(
            "/api/v1/auth/dual-roles/grant/",
            {"user_id": str(teacher.id), "roles": [UserRole.PARENT, UserRole.CLASS_TEACHER]},
            format="json",
        )
        assert response.status_code == 200, response.content
        data = response.json()["data"]
        assert UserRole.PARENT in data["added_roles"]
        assert UserRoleAssignment.objects.filter(user=teacher, role=UserRole.PARENT, is_active=True).exists()

    def test_cannot_switch_ungranted_role(self, tenant, school_admin):
        teacher = User.objects.create_user(
            email="dual.locked@test.edu",
            password="TestPass123!",
            first_name="Only",
            last_name="Teacher",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.post("/api/v1/auth/switch-role/", {"role": UserRole.PARENT}, format="json")
        assert response.status_code == 400

    def test_candidates_include_parents_without_portal_user(self, tenant, school_admin):
        from apps.students.models import Parent

        Parent.objects.create(
            tenant=tenant,
            first_name="Mary",
            last_name="Guardian",
            email="mary.guardian@parents.test",
            phone="+256700000001",
        )
        # staff user still appears
        User.objects.create_user(
            email="staff.only@test.edu",
            password="TestPass123!",
            first_name="Staff",
            last_name="Only",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.get("/api/v1/auth/dual-roles/candidates/", {"q": "Mary"})
        assert response.status_code == 200, response.content
        rows = response.json()["data"]["results"]
        assert any(r.get("directory") == "parent" and "Mary" in r.get("full_name", "") for r in rows)
        assert any(r.get("needs_portal_account") for r in rows)

        # Grant teacher role to parent directory row → creates portal user
        parent_row = next(r for r in rows if r.get("source") == "parent")
        grant = client.post(
            "/api/v1/auth/dual-roles/grant/",
            {"parent_id": parent_row["parent_id"], "roles": [UserRole.TEACHER]},
            format="json",
        )
        assert grant.status_code == 200, grant.content
        body = grant.json()["data"]
        assert UserRole.TEACHER in body["added_roles"] or UserRole.TEACHER in body["available_roles"]
        assert body.get("user_id")
        user = User.objects.get(pk=body["user_id"])
        assert user.email.lower() == "mary.guardian@parents.test"
        assert UserRole.PARENT in body["available_roles"]
        assert UserRole.TEACHER in body["available_roles"]
