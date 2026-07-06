import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from apps.communication.models import Announcement, Broadcast, EmailMessage
from apps.communication.services.messaging import (
    MessagingError,
    publish_announcement,
    send_email_message,
    send_school_broadcast,
)
from apps.platform.services.email_config import sync_email_settings_from_env
from apps.staff.models import Staff
from apps.subscriptions.services import assign_plan_features

DELIVERABLE_TEST_EMAIL = "teacher@greenwoodacademy.org"


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


def _enable_communication_features(tenant):
    plan = tenant.active_subscription.plan
    assign_plan_features(plan, [
        "announcements",
        "broadcast_messaging",
        "email_templates",
        "staff_management",
        "notifications",
    ])


def _ensure_staff_recipient(tenant, user):
    Staff.objects.get_or_create(
        tenant=tenant,
        email=DELIVERABLE_TEST_EMAIL,
        defaults={
            "user": user,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "employee_id": "T001",
            "status": "active",
            "date_joined": timezone.now().date(),
        },
    )
    if user.email != DELIVERABLE_TEST_EMAIL:
        user.email = DELIVERABLE_TEST_EMAIL
        user.save(update_fields=["email", "updated_at"])


@pytest.mark.django_db
class TestSchoolMessaging:
    def test_sync_email_settings_from_env(self, smtp_settings):
        record = sync_email_settings_from_env()
        assert record is not None
        assert record.host == "smtp.gmail.com"
        assert record.is_active is True
        assert record.from_email == "client.apexhub@gmail.com"

    @override_settings(INTEGRATION_LIVE_DISPATCH=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_email_message_updates_status(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        email_message = EmailMessage.objects.create(
            tenant=school_admin.tenant,
            recipient_email=DELIVERABLE_TEST_EMAIL,
            subject="Fee Reminder",
            body="Please pay outstanding fees.",
            status="pending",
        )

        result = send_email_message(email_message)
        email_message.refresh_from_db()

        assert result["success"] is True
        assert email_message.status == "sent"
        assert email_message.sent_at is not None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [DELIVERABLE_TEST_EMAIL]

    def test_publish_announcement_sends_email(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        _ensure_staff_recipient(school_admin.tenant, school_admin)
        announcement = Announcement.objects.create(
            tenant=school_admin.tenant,
            title="Term Opening",
            content="School reopens next Monday.",
            target_audience="staff",
            channels=["email", "notification"],
            priority="normal",
            publish_date=timezone.now(),
            is_published=False,
        )

        result = publish_announcement(announcement)
        announcement.refresh_from_db()

        assert announcement.is_published is True
        assert "email" in result["channels"]
        assert result["delivered_count"] >= 1
        assert len(mail.outbox) >= 1

    def test_send_school_broadcast_email_channel(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        _ensure_staff_recipient(school_admin.tenant, school_admin)
        broadcast = Broadcast.objects.create(
            tenant=school_admin.tenant,
            title="Urgent Notice",
            message="Staff meeting at 3 PM.",
            channels=["email"],
            status="draft",
        )

        result = send_school_broadcast(broadcast)
        broadcast.refresh_from_db()

        assert broadcast.status == "sent"
        assert broadcast.sent_at is not None
        assert result["delivered_count"] >= 1
        assert len(mail.outbox) >= 1

    def test_publish_without_email_addresses_raises(self, school_admin, smtp_settings):
        sync_email_settings_from_env()
        announcement = Announcement.objects.create(
            tenant=school_admin.tenant,
            title="No Emails",
            content="Nobody to email.",
            target_audience="parents",
            channels=["email"],
            publish_date=timezone.now(),
            is_published=False,
        )

        with pytest.raises(MessagingError, match="No deliverable email"):
            publish_announcement(announcement)

    def test_publish_already_published_raises(self, school_admin):
        announcement = Announcement.objects.create(
            tenant=school_admin.tenant,
            title="Done",
            content="Already live.",
            target_audience="all",
            publish_date=timezone.now(),
            is_published=True,
        )

        with pytest.raises(MessagingError):
            publish_announcement(announcement)

    def test_api_publish_announcement(self, api_client, school_admin, smtp_settings):
        _enable_communication_features(school_admin.tenant)
        sync_email_settings_from_env()
        _ensure_staff_recipient(school_admin.tenant, school_admin)
        announcement = Announcement.objects.create(
            tenant=school_admin.tenant,
            title="Sports Day",
            content="Join us Friday for sports day.",
            target_audience="all",
            channels=["email"],
            publish_date=timezone.now(),
            is_published=False,
        )

        api_client.force_authenticate(user=school_admin)
        response = api_client.post(f"/api/v1/communication/announcements/{announcement.id}/publish/")
        assert response.status_code == 200
        assert response.data["success"] is True

        announcement.refresh_from_db()
        assert announcement.is_published is True

    def test_api_send_broadcast(self, api_client, school_admin, smtp_settings):
        _enable_communication_features(school_admin.tenant)
        sync_email_settings_from_env()
        _ensure_staff_recipient(school_admin.tenant, school_admin)
        broadcast = Broadcast.objects.create(
            tenant=school_admin.tenant,
            title="Holiday Notice",
            message="School closes next week.",
            channels=["email"],
            status="draft",
        )

        api_client.force_authenticate(user=school_admin)
        response = api_client.post(f"/api/v1/communication/broadcasts/{broadcast.id}/send/")
        assert response.status_code == 200
        assert response.data["success"] is True

        broadcast.refresh_from_db()
        assert broadcast.status == "sent"

    def test_delete_all_announcements(self, api_client, school_admin):
        _enable_communication_features(school_admin.tenant)
        Announcement.objects.create(
            tenant=school_admin.tenant,
            title="Old",
            content="Remove me.",
            target_audience="all",
            publish_date=timezone.now(),
        )
        api_client.force_authenticate(user=school_admin)
        response = api_client.post("/api/v1/communication/announcements/delete_all/")
        assert response.status_code == 200
        assert response.data["deleted_count"] == 1
        assert Announcement.objects.filter(tenant=school_admin.tenant, is_deleted=False).count() == 0