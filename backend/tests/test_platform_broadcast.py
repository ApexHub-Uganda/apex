import pytest
from django.utils import timezone

from apps.platform.models import PlatformBroadcast, PlatformBroadcastDelivery
from apps.platform.services.broadcasts import (
    BroadcastError,
    cancel_platform_broadcast,
    delete_platform_broadcast,
    duplicate_platform_broadcast,
    preview_audience,
    process_scheduled_broadcasts,
    schedule_platform_broadcast,
    send_platform_broadcast,
)


@pytest.mark.django_db
class TestPlatformBroadcasts:
    def test_preview_audience_counts_school_admin(self, school_admin):
        result = preview_audience(audience="basic", channels=["email", "sms"])
        assert result["total_recipients"] >= 1
        assert "email" in result["channel_stats"]
        assert result["channel_stats"]["email"]["reachable"] >= 1

    def test_super_admin_can_create_broadcast(self, api_client, super_admin):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            "/api/v1/platform/broadcasts/",
            {
                "title": "System Notice",
                "message": "Please review the latest platform update.",
                "channels": ["email", "whatsapp"],
                "audience": "all",
                "severity": "info",
                "starts_at": timezone.now().isoformat(),
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.data.get("data", response.data)
        assert payload["channels"] == ["email", "whatsapp"]
        assert payload["status"] == "draft"

    def test_send_broadcast_all_audience(
        self, api_client, super_admin, school_admin,
    ):
        broadcast = PlatformBroadcast.objects.create(
            title="All Schools Notice",
            message="Platform-wide update.",
            channels=["email"],
            audience="all",
            status="draft",
            severity="info",
            starts_at=timezone.now(),
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f"/api/v1/platform/broadcasts/{broadcast.id}/send/")
        assert response.status_code == 200

        broadcast.refresh_from_db()
        assert broadcast.status == "sent"
        assert broadcast.recipient_count >= 1

    def test_send_broadcast_creates_deliveries_and_notifications(
        self, api_client, super_admin, school_admin,
    ):
        broadcast = PlatformBroadcast.objects.create(
            title="Maintenance Window",
            message="Brief downtime tonight.",
            channels=["email"],
            audience="basic",
            status="draft",
            severity="warning",
            starts_at=timezone.now(),
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f"/api/v1/platform/broadcasts/{broadcast.id}/send/")
        assert response.status_code == 200

        broadcast.refresh_from_db()
        assert broadcast.status == "sent"
        assert broadcast.recipient_count >= 1
        assert PlatformBroadcastDelivery.objects.filter(broadcast=broadcast).exists()

        from apps.communication.models import Notification

        assert Notification.objects.filter(
            recipient=school_admin,
            title=broadcast.title,
        ).exists()

    def test_schedule_and_cancel_broadcast(self, super_admin):
        broadcast = PlatformBroadcast.objects.create(
            title="Future Notice",
            message="Scheduled message.",
            channels=["sms"],
            audience="all",
            status="draft",
            severity="info",
            starts_at=timezone.now() + timezone.timedelta(days=1),
        )

        schedule_platform_broadcast(broadcast)
        broadcast.refresh_from_db()
        assert broadcast.status == "scheduled"

        cancel_platform_broadcast(broadcast)
        broadcast.refresh_from_db()
        assert broadcast.status == "cancelled"
        assert broadcast.cancelled_at is not None

    def test_process_scheduled_broadcasts_sends_due_items(self, school_admin):
        broadcast = PlatformBroadcast.objects.create(
            title="Due Broadcast",
            message="This was scheduled.",
            channels=["email"],
            audience="basic",
            status="scheduled",
            severity="info",
            starts_at=timezone.now() - timezone.timedelta(minutes=5),
        )

        stats = process_scheduled_broadcasts()
        assert stats["processed"] == 1

        broadcast.refresh_from_db()
        assert broadcast.status == "sent"

    def test_duplicate_broadcast_resets_delivery_stats(self, super_admin):
        source = PlatformBroadcast.objects.create(
            title="Sent Notice",
            message="Already delivered.",
            channels=["email"],
            audience="all",
            status="sent",
            severity="info",
            starts_at=timezone.now(),
            sent_at=timezone.now(),
            recipient_count=3,
            delivered_count=2,
            failed_count=1,
        )

        copy = duplicate_platform_broadcast(source, actor=super_admin)
        assert copy.title.endswith("(Copy)")
        assert copy.status == "draft"
        assert copy.recipient_count == 0
        assert copy.delivered_count == 0

    def test_super_admin_can_delete_sent_broadcast(self, api_client, super_admin, school_admin):
        broadcast = PlatformBroadcast.objects.create(
            title="Old Notice",
            message="Already sent message.",
            channels=["email"],
            audience="basic",
            status="sent",
            severity="info",
            starts_at=timezone.now(),
            sent_at=timezone.now(),
            recipient_count=1,
        )
        PlatformBroadcastDelivery.objects.create(
            broadcast=broadcast,
            recipient=school_admin,
            tenant=school_admin.tenant,
            channel="email",
            recipient_email=school_admin.email,
            status="failed",
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(f"/api/v1/platform/broadcasts/{broadcast.id}/")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert not PlatformBroadcast.objects.filter(pk=broadcast.id).exists()
        assert PlatformBroadcastDelivery.objects.filter(broadcast_id=broadcast.id).count() == 0

    def test_delete_platform_broadcast_service_removes_deliveries(self, super_admin, school_admin):
        broadcast = PlatformBroadcast.objects.create(
            title="Remove Me",
            message="Cleanup test.",
            channels=["sms"],
            audience="all",
            status="scheduled",
            severity="warning",
            starts_at=timezone.now() + timezone.timedelta(days=1),
        )
        PlatformBroadcastDelivery.objects.create(
            broadcast=broadcast,
            channel="sms",
            recipient_phone="+15550001111",
            status="pending",
        )

        result = delete_platform_broadcast(broadcast, actor=super_admin)
        assert result["previous_status"] == "scheduled"
        assert result["deliveries_removed"] == 1
        assert not PlatformBroadcast.objects.filter(title="Remove Me").exists()

    def test_send_requires_channels(self, super_admin):
        broadcast = PlatformBroadcast.objects.create(
            title="No Channels",
            message="Missing delivery modes.",
            channels=[],
            audience="all",
            status="draft",
            severity="info",
            starts_at=timezone.now(),
        )

        with pytest.raises(BroadcastError):
            send_platform_broadcast(broadcast, actor=super_admin)