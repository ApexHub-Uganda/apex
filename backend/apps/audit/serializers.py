from rest_framework import serializers

from apps.audit.models import AuditLog


CATEGORY_LABELS = {
    "auth": "Authentication",
    "login": "Authentication",
    "logout": "Authentication",
    "session": "Authentication",
    "tenant": "Schools",
    "school": "Schools",
    "subscription": "Billing",
    "payment": "Billing",
    "plan": "Billing",
    "invoice": "Billing",
    "user": "Users",
    "account": "Users",
    "profile": "Users",
    "student": "Academics",
    "staff": "Academics",
    "class": "Academics",
    "attendance": "Academics",
    "academic": "Academics",
    "broadcast": "Communication",
    "notification": "Communication",
    "email": "Communication",
    "sms": "Communication",
    "platform": "System",
    "settings": "System",
    "health": "System",
}


def get_category_label(resource_type: str) -> str:
    return CATEGORY_LABELS.get((resource_type or "").lower(), resource_type or "General")


def get_status_label(status_code: int | None) -> str:
    if status_code is None:
        return "Unknown"
    if 200 <= status_code < 400:
        return "Success"
    return "Failed"


class AuditLogListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    ip = serializers.CharField(source="ip_address", read_only=True, allow_null=True)
    timestamp = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, allow_null=True)
    category = serializers.SerializerMethodField()
    category_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "tenant", "tenant_name", "user", "action", "resource_type",
            "category", "category_label", "summary", "status_code", "status_label",
            "ip", "timestamp", "created_at",
        ]

    def get_user(self, obj: AuditLog) -> str:
        return obj.user.email if obj.user else "System"

    def get_summary(self, obj: AuditLog) -> str:
        if obj.description:
            return obj.description[:120]
        if obj.resource_id:
            return f"{obj.action} on {obj.resource_type} ({obj.resource_id})"
        return f"{obj.action} on {obj.resource_type}"

    def get_timestamp(self, obj: AuditLog) -> str:
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def get_category(self, obj: AuditLog) -> str:
        return (obj.resource_type or "general").lower()

    def get_category_label(self, obj: AuditLog) -> str:
        return get_category_label(obj.resource_type)

    def get_status_label(self, obj: AuditLog) -> str:
        return get_status_label(obj.status_code)


class AuditLogDetailSerializer(AuditLogListSerializer):
    resource = serializers.SerializerMethodField()
    user_email = serializers.CharField(source="user.email", read_only=True, allow_null=True)

    class Meta(AuditLogListSerializer.Meta):
        fields = AuditLogListSerializer.Meta.fields + [
            "user_email", "resource", "resource_id", "description", "changes",
            "ip_address", "user_agent", "request_method", "request_path",
        ]

    def get_resource(self, obj: AuditLog) -> str:
        if obj.description:
            return obj.description
        if obj.resource_id:
            return f"{obj.resource_type} ({obj.resource_id})"
        return obj.resource_type


class AuditLogSerializer(AuditLogDetailSerializer):
    """Backward-compatible alias."""
    pass