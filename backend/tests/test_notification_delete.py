"""Notification delete/hide behaviour for school admins and super admins."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.communication.models import FeedItemDismissal, Notification
from apps.platform.models import PlatformNotification, PlatformNotificationReceipt


@pytest.mark.django_db
class TestSchoolAdminNotificationDelete:
    def test_feed_delete_one_notification(self, api_client, school_admin):
        notification = Notification.objects.create(
            recipient=school_admin,
            tenant=school_admin.tenant,
            title="Fee reminder",
            message="Term fees are due.",
        )
        api_client.force_authenticate(user=school_admin)

        response = api_client.post(
            "/api/v1/auth/notifications/feed/",
            {"action": "delete_one", "item_id": str(notification.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_deleted is True

        feed = api_client.get("/api/v1/auth/notifications/feed/")
        item_ids = [item["id"] for item in feed.data["data"]["items"]]
        assert str(notification.id) not in item_ids

    def test_feed_delete_all_notifications(self, api_client, school_admin):
        Notification.objects.create(
            recipient=school_admin,
            tenant=school_admin.tenant,
            title="One",
            message="First",
        )
        Notification.objects.create(
            recipient=school_admin,
            tenant=school_admin.tenant,
            title="Two",
            message="Second",
        )
        api_client.force_authenticate(user=school_admin)

        response = api_client.post(
            "/api/v1/auth/notifications/feed/",
            {"action": "delete_all"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(recipient=school_admin, is_deleted=False).count() == 0

    def test_feed_delete_synthetic_item(self, api_client, school_admin):
        api_client.force_authenticate(user=school_admin)
        item_id = "plan-ad-test"

        response = api_client.post(
            "/api/v1/auth/notifications/feed/",
            {"action": "delete_one", "item_id": item_id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert FeedItemDismissal.objects.filter(user=school_admin, item_id=item_id).exists()

        feed = api_client.get("/api/v1/auth/notifications/feed/")
        item_ids = [item["id"] for item in feed.data["data"]["items"]]
        assert item_id not in item_ids


@pytest.mark.django_db
class TestSuperAdminNotificationDelete:
    def _create_platform_notification(self, tenant):
        return PlatformNotification.objects.create(
            notification_type="school_registration",
            title="New school",
            message="A school registered.",
            tenant=tenant,
            status="pending",
        )

    def test_hide_one_platform_notification(self, api_client, super_admin, tenant):
        notification = self._create_platform_notification(tenant)
        api_client.force_authenticate(user=super_admin)

        response = api_client.post(
            f"/api/v1/platform/notifications/{notification.id}/delete_notification/",
        )

        assert response.status_code == status.HTTP_200_OK
        receipt = PlatformNotificationReceipt.objects.get(
            notification=notification,
            user=super_admin,
        )
        assert receipt.is_deleted is True

        list_response = api_client.get("/api/v1/platform/notifications/")
        ids = [item["id"] for item in list_response.data["results"]]
        assert str(notification.id) not in ids

    def test_hide_all_platform_notifications(self, api_client, super_admin, tenant):
        first = self._create_platform_notification(tenant)
        second = PlatformNotification.objects.create(
            notification_type="trial_request",
            title="Trial request",
            message="Trial requested.",
            tenant=tenant,
            status="approved",
        )
        api_client.force_authenticate(user=super_admin)

        response = api_client.post("/api/v1/platform/notifications/delete_all/")

        assert response.status_code == status.HTTP_200_OK
        for notification in (first, second):
            receipt = PlatformNotificationReceipt.objects.get(
                notification=notification,
                user=super_admin,
            )
            assert receipt.is_deleted is True

        list_response = api_client.get("/api/v1/platform/notifications/")
        assert list_response.data["count"] == 0

    def test_feed_delete_one_for_super_admin(self, api_client, super_admin, tenant):
        notification = self._create_platform_notification(tenant)
        api_client.force_authenticate(user=super_admin)

        response = api_client.post(
            "/api/v1/auth/notifications/feed/",
            {"action": "delete_one", "item_id": str(notification.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        receipt = PlatformNotificationReceipt.objects.get(
            notification=notification,
            user=super_admin,
        )
        assert receipt.is_deleted is True