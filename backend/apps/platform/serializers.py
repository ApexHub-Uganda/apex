from rest_framework import serializers

from apps.platform.models import (
    APIKey,
    CallSetting,
    EmailSetting,
    GlobalSetting,
    PlatformBroadcast,
    PlatformNews,
    PlatformNotification,
    SMSSetting,
    SystemHealthLog,
)


class GlobalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSetting
        fields = "__all__"


class EmailSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSetting
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}


class SMSSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSSetting
        fields = "__all__"
        extra_kwargs = {"api_secret": {"write_only": True}}


class CallSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallSetting
        fields = "__all__"
        extra_kwargs = {"api_secret": {"write_only": True}}


class PlatformNotificationSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="tenant.name", read_only=True)
    school_id = serializers.UUIDField(source="tenant.id", read_only=True)
    school_code = serializers.CharField(source="tenant.code", read_only=True)
    registration_type = serializers.CharField(source="tenant.registration_type", read_only=True)
    action_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PlatformNotification
        fields = [
            "id", "notification_type", "title", "message", "tenant", "school_id",
            "school_name", "school_code", "registration_type", "status", "priority",
            "metadata", "is_read", "read_at", "action_taken_by", "action_by_name",
            "action_taken_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "notification_type", "title", "message", "tenant", "status",
            "priority", "metadata", "action_taken_by", "action_taken_at",
            "created_at", "updated_at",
        ]

    def get_action_by_name(self, obj: PlatformNotification) -> str:
        if obj.action_taken_by:
            return obj.action_taken_by.full_name or obj.action_taken_by.email
        return ""


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ["id", "name", "key_prefix", "tenant", "scopes", "is_active", "expires_at", "last_used_at", "created_at"]
        read_only_fields = ["id", "key_prefix", "last_used_at", "created_at"]


class PlatformNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformNews
        fields = "__all__"


class PlatformBroadcastSerializer(serializers.ModelSerializer):
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)
    sent_at_display = serializers.SerializerMethodField()

    class Meta:
        model = PlatformBroadcast
        fields = [
            "id", "title", "message", "audience", "audience_display", "status",
            "severity", "is_active", "starts_at", "ends_at", "sent_at",
            "sent_at_display", "created_at", "updated_at",
        ]

    def get_sent_at_display(self, obj: PlatformBroadcast) -> str:
        if obj.sent_at:
            return obj.sent_at.strftime("%Y-%m-%d")
        if obj.status == "sent" and obj.starts_at:
            return obj.starts_at.strftime("%Y-%m-%d")
        return "—"

    def create(self, validated_data: dict) -> PlatformBroadcast:
        from django.utils import timezone

        if validated_data.get("status") == "sent" and not validated_data.get("sent_at"):
            validated_data["sent_at"] = timezone.now()
        return super().create(validated_data)


class PlatformSettingsSerializer(serializers.Serializer):
    platform_name = serializers.CharField(max_length=255, required=False)
    platform_tagline = serializers.CharField(max_length=255, required=False, allow_blank=True)
    support_email = serializers.EmailField(required=False)
    default_plan = serializers.SlugField(required=False)
    max_upload_size = serializers.IntegerField(min_value=1, max_value=500, required=False)
    maintenance_mode = serializers.BooleanField(required=False)
    default_timezone = serializers.CharField(max_length=50, required=False)
    default_country = serializers.CharField(max_length=100, required=False)


class SystemHealthLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemHealthLog
        fields = "__all__"