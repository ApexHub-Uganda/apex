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

    def test_dual_role_appears_in_staff_and_parent_lists(self, tenant, school_admin):
        from apps.students.models import Parent
        from apps.staff.models import Staff

        teacher = User.objects.create_user(
            email="both.roles@test.edu",
            password="TestPass123!",
            first_name="Both",
            last_name="Roles",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=teacher, roles=[UserRole.PARENT], actor=school_admin)
        teacher.refresh_from_db()

        assert Parent.objects.filter(tenant=tenant, user=teacher, is_deleted=False).exists()
        assert Staff.objects.filter(tenant=tenant, user=teacher, is_deleted=False).exists()

    def test_revoke_parent_cleans_directory_and_links(self, tenant, school_admin):
        from apps.accounts.dual_roles import revoke_role
        from apps.students.models import Parent, Student
        from datetime import date

        teacher = User.objects.create_user(
            email="revoke.parent@test.edu",
            password="TestPass123!",
            first_name="Revoke",
            last_name="Parent",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=teacher, roles=[UserRole.PARENT], actor=school_admin)
        parent = Parent.objects.get(user=teacher, tenant=tenant, is_deleted=False)
        student = Student.objects.create(
            tenant=tenant,
            admission_number="REV-001",
            first_name="Kid",
            last_name="Revoke",
            date_of_birth=date(2014, 1, 1),
            enrollment_date=date(2024, 1, 1),
            gender="male",
            status="active",
        )
        student.parents.add(parent)
        assert parent.children.count() == 1

        result = revoke_role(user=teacher, role=UserRole.PARENT, actor=school_admin)
        assert result["revoked"] == UserRole.PARENT
        assert result["cleanup"].get("parent_removed") is True
        assert not Parent.objects.filter(pk=parent.pk, is_deleted=False).exists()
        assert UserRole.PARENT not in list_user_roles(teacher)
        assert UserRole.TEACHER in list_user_roles(teacher)

    def test_staff_check_in_shared_across_dual_roles(self, tenant, school_admin):
        """One GPS check-in for the person is visible under every staff portal role."""
        from apps.attendance.staff_geo_attendance import staff_attendance_status, staff_check_in
        from apps.accounts.dual_roles import grant_roles, switch_role
        from apps.staff.models import Staff

        user = User.objects.create_user(
            email="shared.signin@test.edu",
            password="TestPass123!",
            first_name="Shared",
            last_name="Signin",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=user, roles=[UserRole.BURSAR], actor=school_admin)
        Staff.objects.filter(user=user).update(is_deleted=False)
        # Ensure staff row
        from apps.accounts.dual_roles import _ensure_profile_for_role
        _ensure_profile_for_role(user, UserRole.TEACHER, actor=school_admin)

        # Check-in as teacher without webauthn by calling lower path carefully —
        # staff_check_in requires request for webauthn; test status sharing via record
        from apps.attendance.models import AttendanceRecord
        from django.utils import timezone
        staff = Staff.objects.filter(user=user, is_deleted=False).first()
        assert staff is not None
        AttendanceRecord.objects.create(
            tenant=tenant,
            attendee_type="staff",
            staff=staff,
            date=timezone.localdate(),
            status="present",
            check_in=timezone.localtime().time().replace(microsecond=0),
            marked_by=user,
            created_by=user,
            updated_by=user,
        )
        switch_role(user=user, role=UserRole.BURSAR)
        status = staff_attendance_status(tenant=tenant, user=user)
        assert status["checked_in"] is True
        assert status["shared_across_roles"] is True

    def test_revoke_active_role_once_does_not_resurrect(self, tenant, school_admin):
        """
        Regression: first revoke used to re-activate the role via ensure_primary_assignment
        when it was the user's active User.role — requiring a second revoke click.
        """
        from apps.accounts.dual_roles import revoke_role
        from apps.accounts.models import UserRoleAssignment

        teacher = User.objects.create_user(
            email="once.revoke@test.edu",
            password="TestPass123!",
            first_name="Once",
            last_name="Revoke",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=teacher, roles=[UserRole.PARENT], actor=school_admin)
        teacher.refresh_from_db()
        assert teacher.role == UserRole.TEACHER
        assert set(list_user_roles(teacher)) >= {UserRole.TEACHER, UserRole.PARENT}

        # Revoke the ACTIVE role once
        result = revoke_role(user=teacher, role=UserRole.TEACHER, actor=school_admin)
        teacher.refresh_from_db()

        assert UserRole.TEACHER not in result["available_roles"]
        assert UserRole.TEACHER not in list_user_roles(teacher)
        assert UserRole.PARENT in list_user_roles(teacher)
        assert teacher.role == UserRole.PARENT
        assert not UserRoleAssignment.objects.filter(
            user=teacher, role=UserRole.TEACHER, is_active=True,
        ).exists()

        # Calling list_user_roles again must not resurrect teacher
        assert UserRole.TEACHER not in list_user_roles(teacher)

    def test_revoke_preview_lists_linked_students(self, tenant, school_admin):
        from apps.accounts.dual_roles import preview_revoke_role
        from apps.students.models import Parent, Student
        from datetime import date

        teacher = User.objects.create_user(
            email="preview.revoke@test.edu",
            password="TestPass123!",
            first_name="Preview",
            last_name="Revoke",
            role=UserRole.TEACHER,
            tenant=tenant,
            is_active=True,
        )
        grant_roles(user=teacher, roles=[UserRole.PARENT], actor=school_admin)
        parent = Parent.objects.get(user=teacher, is_deleted=False)
        student = Student.objects.create(
            tenant=tenant,
            admission_number="PRV-001",
            first_name="Linked",
            last_name="Child",
            date_of_birth=date(2014, 1, 1),
            enrollment_date=date(2024, 1, 1),
            gender="female",
            status="active",
        )
        student.parents.add(parent)
        impact = preview_revoke_role(user=teacher, role=UserRole.PARENT)
        assert impact["will_remove_parent_profile"] is True
        assert impact["linked_students_count"] == 1
        assert impact["warnings"]
