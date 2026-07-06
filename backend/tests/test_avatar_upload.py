"""Profile picture upload and removal tests."""
from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.avatar_service import user_has_avatar
from apps.accounts.models import UserProfilePicture
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff


def _make_image(name: str = "avatar.png") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color=(30, 120, 200)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


@pytest.fixture
def hr_staff(db, tenant):
    return onboard_staff(
        tenant,
        data={
            "first_name": "HR",
            "last_name": "Staff",
            "email": "avatar.hr@test.edu",
            "phone": "+254700000088",
            "portal_role": UserRole.HR_MANAGER,
            "date_joined": "2025-01-01",
        },
    )


@pytest.mark.django_db
class TestAvatarUpload:
    def test_upload_and_delete_avatar(self, tenant, hr_staff):
        user = hr_staff.user
        client = APIClient()
        client.force_authenticate(user=user)

        upload = client.post("/api/v1/auth/me/avatar/", {"avatar": _make_image()}, format="multipart")
        assert upload.status_code == 200
        data = upload.json()["data"]
        assert data["has_avatar"] is True
        assert data["avatar_url"]
        assert UserProfilePicture.objects.filter(user=user).exists()
        assert user_has_avatar(user)

        hr_staff.refresh_from_db()
        assert hr_staff.photo

        delete = client.delete("/api/v1/auth/me/avatar/")
        assert delete.status_code == 200
        assert delete.json()["data"]["has_avatar"] is False
        assert not UserProfilePicture.objects.filter(user=user).exists()

        hr_staff.refresh_from_db()
        assert not hr_staff.photo

    def test_rejects_invalid_file_type(self, tenant, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        bad = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")

        response = client.post("/api/v1/auth/me/avatar/", {"avatar": bad}, format="multipart")
        assert response.status_code == 400

    def test_me_profile_includes_avatar_fields(self, tenant, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        client.post("/api/v1/auth/me/avatar/", {"avatar": _make_image()}, format="multipart")

        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["has_avatar"] is True
        assert payload["avatar_url"]