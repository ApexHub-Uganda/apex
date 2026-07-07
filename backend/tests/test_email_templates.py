"""Branded outbound email template tests."""
from __future__ import annotations

import pytest
from django.core import mail
from django.test import override_settings

from apps.core.email_templates import (
    build_announcement_email,
    build_branded_email,
    build_password_reset_email,
    build_platform_broadcast_email,
    build_school_broadcast_email,
)
from apps.communication.services.messaging import publish_announcement, send_email_message
from apps.communication.models import Announcement, EmailMessage
from apps.platform.services.broadcasts import send_platform_broadcast
from apps.platform.models import PlatformBroadcast
from apps.platform.services.email_config import sync_email_settings_from_env
from django.utils import timezone


@pytest.mark.django_db
class TestEmailTemplates:
    def test_password_reset_template_includes_otp_and_html(self):
        branded = build_password_reset_email(
            first_name="Jane",
            email="jane@school.edu",
            otp="482910",
            expires_minutes=10,
        )
        assert "482910" in branded.html_body
        assert "Verification code" in branded.html_body
        assert "482910" in branded.text_body
        assert "<!DOCTYPE html>" in branded.html_body

    def test_announcement_template_escapes_html(self):
        branded = build_announcement_email(
            tenant=None,
            title="Sports <script>",
            content="Join us & celebrate.",
            priority="urgent",
        )
        assert "<script>" not in branded.html_body
        assert "Sports &lt;script&gt;" in branded.html_body
        assert "Urgent" in branded.html_body or "urgent" in branded.html_body.lower()

    def test_platform_broadcast_uses_severity_tone(self):
        branded = build_platform_broadcast_email(
            title="Maintenance",
            message="Brief downtime tonight.",
            severity="warning",
        )
        assert "Maintenance" in branded.html_body
        assert "Important" in branded.html_body

    def test_school_broadcast_includes_school_branding(self, school_admin):
        branded = build_school_broadcast_email(
            tenant=school_admin.tenant,
            title="Staff Meeting",
            message="Meet at 3 PM.",
        )
        assert school_admin.tenant.name in branded.html_body
        assert "Broadcast" in branded.html_body

    def test_build_branded_email_supports_multiline_body(self):
        branded = build_branded_email(
            title="Hello",
            body="Line one.\n\nLine two.",
            tone="info",
        )
        assert "Line one." in branded.html_body
        assert "Line two." in branded.html_body


@pytest.fixture
def smtp_settings(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.EMAIL_HOST = "smtp.gmail.com"
    settings.EMAIL_PORT = 587
    settings.EMAIL_USE_TLS = True
    settings.EMAIL_HOST_USER = "client.apexhub@gmail.com"
    settings.EMAIL_HOST_PASSWORD = "app-password"
    settings.DEFAULT_FROM_EMAIL = "client.apexhub@gmail.com"
    settings.INTEGRATION_LIVE_DISPATCH = True
    return settings


@pytest.mark.django_db
class TestBrandedEmailDelivery:
    @override_settings(INTEGRATION_LIVE_DISPATCH=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_direct_email_message_sends_html_alternative(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        email_message = EmailMessage.objects.create(
            tenant=school_admin.tenant,
            recipient_email="teacher@greenwoodacademy.org",
            subject="Fee Reminder",
            body="Please pay outstanding fees.",
            status="pending",
        )
        send_email_message(email_message)
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert len(message.alternatives) == 1
        html, mimetype = message.alternatives[0]
        assert mimetype == "text/html"
        assert "<!DOCTYPE html>" in html
        assert "Fee Reminder" in html

    def test_announcement_email_includes_html(self, school_admin, smtp_settings):
        from apps.staff.models import Staff
        from apps.subscriptions.services import assign_plan_features

        sync_email_settings_from_env()
        assign_plan_features(school_admin.tenant.active_subscription.plan, ["announcements", "staff_management"])
        Staff.objects.get_or_create(
            tenant=school_admin.tenant,
            email="teacher@greenwoodacademy.org",
            defaults={
                "user": school_admin,
                "first_name": school_admin.first_name,
                "last_name": school_admin.last_name,
                "employee_id": "T001",
                "status": "active",
                "date_joined": timezone.now().date(),
            },
        )
        if school_admin.email != "teacher@greenwoodacademy.org":
            school_admin.email = "teacher@greenwoodacademy.org"
            school_admin.save(update_fields=["email", "updated_at"])

        announcement = Announcement.objects.create(
            tenant=school_admin.tenant,
            title="Term Opening",
            content="School reopens next Monday.",
            target_audience="staff",
            channels=["email"],
            priority="normal",
            publish_date=timezone.now(),
            is_published=False,
        )
        publish_announcement(announcement)
        assert len(mail.outbox) >= 1
        html, mimetype = mail.outbox[-1].alternatives[0]
        assert mimetype == "text/html"
        assert "Term Opening" in html
        assert "Announcement" in html

    def test_platform_broadcast_email_includes_html(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        broadcast = PlatformBroadcast.objects.create(
            title="System Notice",
            message="Please review the latest update.",
            channels=["email"],
            audience="basic",
            status="draft",
            severity="info",
            starts_at=timezone.now(),
        )
        send_platform_broadcast(broadcast)
        assert len(mail.outbox) >= 1
        html, mimetype = mail.outbox[-1].alternatives[0]
        assert mimetype == "text/html"
        assert "System Notice" in html