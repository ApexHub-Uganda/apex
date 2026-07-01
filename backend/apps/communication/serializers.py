from rest_framework import serializers
from apps.communication.models import Announcement, Broadcast, EmailMessage, Notification, SMSMessage, SupportTicket
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class SMSMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSMessage
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class EmailMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMessage
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class BroadcastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broadcast
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
