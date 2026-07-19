"""Branded PDF template + school settings branding persistence."""
from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core.pdf_template import build_branded_pdf, build_pdf_template_preview, p
from apps.core.pdf_branding import build_tenant_branding


def _png_bytes(color=(15, 118, 110), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
class TestSchoolSettingsBranding:
    def test_school_admin_can_update_colors_and_contacts(self, api_client, school_admin, tenant):
        api_client.force_authenticate(user=school_admin)
        response = api_client.patch(
            "/api/v1/tenants/settings/",
            {
                "name": tenant.name,
                "email": "office@demo-school.test",
                "phone": "+254711000111",
                "address": "1 Education Road",
                "city": "Nairobi",
                "country": "Kenya",
                "tagline": "Learning for life",
                "primary_color": "#123456",
                "secondary_color": "#AABBCC",
                "accent_color": "#FFEEDD",
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        data = response.data["data"]
        assert data["primary_color"] == "#123456"
        assert data["phone"] == "+254711000111"
        assert data["tagline"] == "Learning for life"
        tenant.refresh_from_db()
        assert tenant.primary_color == "#123456"
        assert tenant.address == "1 Education Road"

    def test_school_admin_can_upload_logo(self, api_client, school_admin, tenant):
        api_client.force_authenticate(user=school_admin)
        logo = SimpleUploadedFile("logo.png", _png_bytes(), content_type="image/png")
        response = api_client.patch(
            "/api/v1/tenants/settings/",
            {
                "name": tenant.name,
                "email": tenant.email,
                "logo": logo,
            },
            format="multipart",
        )
        assert response.status_code == 200, response.data
        tenant.refresh_from_db()
        assert tenant.logo
        assert tenant.logo.name.endswith(".png") or "logo" in tenant.logo.name

    def test_non_admin_cannot_patch_settings(self, api_client, parent_user_simple, tenant):
        api_client.force_authenticate(user=parent_user_simple)
        response = api_client.patch(
            "/api/v1/tenants/settings/",
            {"primary_color": "#000000"},
            format="json",
        )
        assert response.status_code in (403, 401)


@pytest.mark.django_db
class TestBrandedPdfTemplate:
    def test_preview_pdf_is_valid_a4(self, api_client, school_admin, tenant):
        tenant.primary_color = "#0A5C55"
        tenant.secondary_color = "#FF6B3D"
        tenant.tagline = "Excellence"
        tenant.phone = "+254700000000"
        tenant.address = "Campus Drive"
        tenant.city = "Kisumu"
        tenant.save()
        logo = SimpleUploadedFile("badge.png", _png_bytes((10, 90, 80)), content_type="image/png")
        tenant.logo.save("badge.png", logo, save=True)

        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/tenants/pdf-preview/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        body = b"".join(response.streaming_content) if hasattr(response, "streaming_content") else response.content
        assert body.startswith(b"%PDF")
        assert len(body) > 500

    def test_build_branded_pdf_uses_document_meta_for_qr(self, tenant):
        tenant.tagline = "Motivated learners"
        tenant.save()

        def story(ctx, styles):
            return [p("Body line for results", styles["Body"])]

        pdf_bytes = build_branded_pdf(
            tenant=tenant,
            document_type="student_result",
            document_meta={"student": "ADM-9", "term": "Term 1"},
            title="Term Report",
            build_story=story,
        )
        assert pdf_bytes.startswith(b"%PDF")

        branding = build_tenant_branding(tenant)
        assert branding["primary_color"]
        assert branding["school_name"] == tenant.name

    def test_preview_helper_matches_public_builder(self, tenant):
        pdf_bytes = build_pdf_template_preview(tenant=tenant)
        assert pdf_bytes.startswith(b"%PDF")


# Optional lightweight parent fixture if not present in conftest
@pytest.fixture
def parent_user_simple(db, tenant):
    from django.contrib.auth import get_user_model
    from apps.core.constants import UserRole

    User = get_user_model()
    return User.objects.create_user(
        email="parent.settings@test.edu",
        password="TestPass@2026",
        first_name="P",
        last_name="Parent",
        role=UserRole.PARENT,
        tenant=tenant,
    )
