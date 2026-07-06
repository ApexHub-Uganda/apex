from django.utils import timezone
from rest_framework import serializers
from apps.communication.models import Announcement, Broadcast, EmailMessage, Notification, SMSMessage, SupportTicket, TicketReply
from apps.core.email_validation import validate_deliverable_email
from apps.core.serializer_fields import DeliverableEmailField


class AnnouncementSerializer(serializers.ModelSerializer):
    audience = serializers.CharField(source="target_audience", required=False)

    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted",
            "is_published", "publish_date",
        ]

    def validate(self, attrs):
        channels = attrs.get("channels")
        if channels is not None and len(channels) == 0:
            attrs["channels"] = ["email", "notification"]
        return attrs

    def create(self, validated_data):
        if "publish_date" not in validated_data:
            validated_data["publish_date"] = timezone.now()
        if not validated_data.get("channels"):
            validated_data["channels"] = ["email", "notification"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "channels" in validated_data and not validated_data["channels"]:
            validated_data["channels"] = ["email", "notification"]
        return super().update(instance, validated_data)
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
    recipient_email = DeliverableEmailField()

    class Meta:
        model = EmailMessage
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted",
            "status", "sent_at",
        ]


class BroadcastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broadcast
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted",
            "sent_at", "recipient_count",
        ]

    def create(self, validated_data):
        if not validated_data.get("channels"):
            validated_data["channels"] = ["email"]
        return super().create(validated_data)
class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class TicketReplySerializer(serializers.ModelSerializer):
    ticket_subject = serializers.CharField(source="ticket.subject", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketReply
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]

    def get_author_name(self, obj) -> str:
        if obj.author:
            return obj.author.get_full_name() or obj.author.email
        return "Staff"
