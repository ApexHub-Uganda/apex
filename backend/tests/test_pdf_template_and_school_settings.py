"""Branded PDF template + school settings branding persistence."""
from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core.pdf_template import (
    build_branded_pdf,
    build_headed_paper_pdf,
    build_pdf_template_preview,
    encode_document_qr_payload,
    p,
    _draw_qr_code,
    _draw_qr_reportlab_native,
)
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
        before = tenant.primary_color
        response = api_client.patch(
            "/api/v1/tenants/settings/",
            {"primary_color": "#000000"},
            format="json",
        )
        assert response.status_code in (403, 401)
        tenant.refresh_from_db()
        assert tenant.primary_color == before

    def test_teacher_cannot_patch_school_settings(self, api_client, tenant):
        """Teachers must never mutate school branding / institution settings."""
        from django.contrib.auth import get_user_model
        from apps.core.constants import UserRole

        User = get_user_model()
        teacher_user = User.objects.create_user(
            email="teacher.settings.block@test.edu",
            password="TestPass@2026",
            first_name="T",
            last_name="Eacher",
            role=UserRole.TEACHER,
            tenant=tenant,
        )
        api_client.force_authenticate(user=teacher_user)
        before_name = tenant.name
        before_color = tenant.primary_color
        response = api_client.patch(
            "/api/v1/tenants/settings/",
            {
                "name": "Hacked School Name",
                "email": "hacked@example.com",
                "primary_color": "#FF0000",
            },
            format="json",
        )
        assert response.status_code in (403, 401), response.data
        tenant.refresh_from_db()
        assert tenant.name == before_name
        assert tenant.primary_color == before_color


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

    def test_qr_draws_without_optional_qrcode_package(self, tenant, monkeypatch):
        """
        Live servers may lack the optional `qrcode` package (ReportLab still present).
        Header QR must still render via ReportLab's built-in QrCodeWidget.
        """
        import builtins
        import sys

        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "qrcode" or name.startswith("qrcode."):
                raise ModuleNotFoundError("No module named 'qrcode'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked_import)
        # Also drop from sys.modules if already loaded
        for key in list(sys.modules):
            if key == "qrcode" or key.startswith("qrcode."):
                monkeypatch.delitem(sys.modules, key, raising=False)

        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4

        branding = build_tenant_branding(tenant)
        payload = encode_document_qr_payload(
            branding=branding,
            document_type="timetable",
            document_meta={
                "name": "Term 1 Timetable",
                "status": "published",
                "term": "Term 1",
                "class": "S1 East",
            },
        )
        assert "Term 1 Timetable" in payload
        assert "published" in payload
        assert "issued_at" not in payload
        assert "schedule_id" not in payload

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        ok = _draw_qr_code(c, payload, 500, 750, 56)
        assert ok is True, "QR must draw via ReportLab native path without qrcode package"
        assert _draw_qr_reportlab_native(c, payload, 400, 750, 56) is True
        c.showPage()
        c.save()
        assert buf.getvalue().startswith(b"%PDF")
        assert len(buf.getvalue()) > 800

        def story(ctx, styles):
            return [p("Timetable body", styles["Body"])]

        pdf_bytes = build_branded_pdf(
            tenant=tenant,
            document_type="timetable",
            document_meta={
                "name": "Term 1 Timetable",
                "status": "published",
                "term": "Term 1",
                "class": "Whole school",
            },
            title="Timetable — Term 1",
            subtitle="Whole school",
            build_story=story,
            orientation="landscape",
        )
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1500

    def test_headed_paper_pdf_multi_page(self, tenant):
        pdf_bytes = build_headed_paper_pdf(tenant=tenant, page_count=3)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 800
        # Multi-page letterhead should be larger than a single blank page
        single = build_headed_paper_pdf(tenant=tenant, page_count=1)
        assert len(pdf_bytes) > len(single)

    def test_headed_paper_api_staff_ok_parent_denied(
        self, api_client, school_admin, parent_user_simple, tenant,
    ):
        api_client.force_authenticate(user=school_admin)
        ok = api_client.get("/api/v1/auth/me/headed-paper.pdf", {"pages": 2})
        assert ok.status_code == 200, ok.content
        assert ok["Content-Type"] == "application/pdf"
        body = ok.content
        assert body.startswith(b"%PDF")

        api_client.force_authenticate(user=parent_user_simple)
        denied = api_client.get("/api/v1/auth/me/headed-paper.pdf", {"pages": 1})
        assert denied.status_code == 403

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
