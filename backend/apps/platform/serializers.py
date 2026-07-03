from rest_framework import serializers

from apps.platform.models import (
    APIKey,
    CallSetting,
    EmailSetting,
    GlobalSetting,
    PlanAdvertisement,
    PlatformBroadcast,
    PlatformBroadcastDelivery,
    PlatformNews,
    PlatformNotification,
    SMSSetting,
    SystemHealthLog,
    WhatsAppSetting,
)
from apps.platform.services.broadcasts import VALID_CHANNELS, normalize_channels


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


class WhatsAppSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppSetting
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


class PlanAdvertisementSerializer(serializers.ModelSerializer):
    target_plan_name = serializers.SerializerMethodField()
    suggested_plan_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlanAdvertisement
        fields = [
            "id", "target_plan_slug", "target_plan_name", "suggested_plan_slug",
            "suggested_plan_name", "title", "headline", "message", "highlights",
            "cta_label", "cta_url", "status", "status_display", "starts_at", "ends_at",
            "broadcast_at", "broadcast_count", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "broadcast_at", "broadcast_count", "created_by", "created_at", "updated_at",
        ]

    def get_target_plan_name(self, obj: PlanAdvertisement) -> str:
        from apps.platform.services.plan_advertisements import get_plan_label
        return get_plan_label(obj.target_plan_slug)

    def get_suggested_plan_name(self, obj: PlanAdvertisement) -> str:
        from apps.platform.services.plan_advertisements import get_plan_label
        return get_plan_label(obj.suggested_plan_slug)

    def get_created_by_name(self, obj: PlanAdvertisement) -> str:
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return ""

    def validate(self, attrs: dict) -> dict:
        from apps.platform.services.plan_advertisements import get_upgrade_options

        target = attrs.get("target_plan_slug") or getattr(self.instance, "target_plan_slug", None)
        suggested = attrs.get("suggested_plan_slug") or getattr(self.instance, "suggested_plan_slug", None)
        if target and suggested:
            options = get_upgrade_options(target)
            if suggested not in options:
                raise serializers.ValidationError({
                    "suggested_plan_slug": "Suggested plan must be a higher tier than the target plan.",
                })
        return attrs


class PlatformBroadcastDeliverySerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source="tenant.name", read_only=True, default="")

    class Meta:
        model = PlatformBroadcastDelivery
        fields = [
            "id", "channel", "recipient", "recipient_name", "school_name",
            "recipient_email", "recipient_phone", "status", "error_message",
            "provider_reference", "sent_at", "created_at",
        ]

    def get_recipient_name(self, obj: PlatformBroadcastDelivery) -> str:
        if obj.recipient:
            return obj.recipient.full_name or obj.recipient.email
        return obj.recipient_email or obj.recipient_phone or "—"


class PlatformBroadcastSerializer(serializers.ModelSerializer):
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)
    channels_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    sent_at_display = serializers.SerializerMethodField()

    class Meta:
        model = PlatformBroadcast
        fields = [
            "id", "title", "message", "channels", "channels_display",
            "audience", "audience_display", "status", "severity", "is_active",
            "starts_at", "ends_at", "sent_at", "sent_at_display", "cancelled_at",
            "recipient_count", "delivered_count", "failed_count", "skipped_count",
            "created_by", "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "sent_at", "cancelled_at", "recipient_count", "delivered_count",
            "failed_count", "skipped_count", "created_by",
        ]

    def get_channels_display(self, obj: PlatformBroadcast) -> list[str]:
        labels = {"email": "Email", "sms": "SMS", "whatsapp": "WhatsApp"}
        return [labels.get(ch, ch) for ch in normalize_channels(obj.channels)]

    def get_created_by_name(self, obj: PlatformBroadcast) -> str:
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return ""

    def get_sent_at_display(self, obj: PlatformBroadcast) -> str:
        if obj.sent_at:
            return obj.sent_at.strftime("%Y-%m-%d %H:%M")
        if obj.status == "scheduled" and obj.starts_at:
            return f"Scheduled {obj.starts_at.strftime('%Y-%m-%d %H:%M')}"
        return "—"

    def validate_channels(self, value: list[str]) -> list[str]:
        channels = normalize_channels(value)
        if value and not channels:
            raise serializers.ValidationError(
                "Channels must include one or more of: email, sms, whatsapp.",
            )
        invalid = [ch for ch in value if str(ch).strip().lower() not in VALID_CHANNELS]
        if invalid:
            raise serializers.ValidationError(f"Invalid channels: {', '.join(invalid)}")
        return channels

    def validate(self, attrs: dict) -> dict:
        status = attrs.get("status", getattr(self.instance, "status", "draft"))
        channels = attrs.get("channels", getattr(self.instance, "channels", []))
        if status in ("scheduled", "sent") and not normalize_channels(channels):
            raise serializers.ValidationError({
                "channels": "At least one channel is required for scheduled or sent broadcasts.",
            })
        return attrs


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