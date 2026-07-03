from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils import timezone
from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.communication.models import Announcement, Broadcast, EmailMessage, Notification, SMSMessage, SupportTicket
from apps.communication.serializers import (
    AnnouncementSerializer, BroadcastSerializer, EmailMessageSerializer,
    NotificationSerializer, SMSMessageSerializer, SupportTicketSerializer,
)

class AnnouncementViewSet(BaseModelViewSet):
    required_feature_key = "announcements"
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["target_audience", "priority", "is_published"]

class NotificationViewSet(BaseModelViewSet):
    required_feature_key = "notifications"
    queryset = Notification.objects.select_related("recipient")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, TenantActivePermission]
    filterset_fields = ["is_read", "notification_type"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user, is_deleted=False)

    @action(detail=True, methods=["post"])
    def mark_read(self, request: Request, pk: str = None) -> Response:
        n = self.get_object()
        n.is_read = True
        n.read_at = timezone.now()
        n.save()
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request: Request) -> Response:
        from apps.communication.services import mark_all_user_notifications_read

        count = mark_all_user_notifications_read(request.user)
        return Response({"success": True, "message": f"{count} notifications marked as read."})

    @action(detail=True, methods=["post"])
    def delete_notification(self, request: Request, pk: str = None) -> Response:
        from apps.communication.services import delete_user_notification

        deleted = delete_user_notification(request.user, pk)
        if not deleted:
            return Response({"success": False, "error": {"message": "Notification not found."}}, status=404)
        return Response({"success": True, "message": "Notification deleted."})

    @action(detail=False, methods=["post"])
    def delete_all(self, request: Request) -> Response:
        from apps.communication.services import delete_all_user_notifications

        count = delete_all_user_notifications(request.user)
        return Response({"success": True, "message": f"{count} notification(s) deleted."})

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        from apps.communication.services import (
            get_navbar_user_notifications,
            get_unread_user_notifications,
        )

        return Response({
            "success": True,
            "data": {
                "unread_count": get_unread_user_notifications(request.user),
                "items": get_navbar_user_notifications(request.user, limit=5),
            },
        })

class SMSMessageViewSet(BaseModelViewSet):
    required_feature_key = "sms_communication"
    queryset = SMSMessage.objects.all()
    serializer_class = SMSMessageSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]

class EmailMessageViewSet(BaseModelViewSet):
    required_feature_key = "email_templates"
    queryset = EmailMessage.objects.all()
    serializer_class = EmailMessageSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]

class BroadcastViewSet(BaseModelViewSet):
    required_feature_key = "broadcast_messaging"
    queryset = Broadcast.objects.all()
    serializer_class = BroadcastSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]

class SupportTicketViewSet(BaseModelViewSet):
    required_feature_key = "support_tickets"
    queryset = SupportTicket.objects.select_related("submitted_by", "assigned_to")
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated, TenantActivePermission]
    filterset_fields = ["status", "category", "priority"]
    search_fields = ["ticket_number", "subject"]
