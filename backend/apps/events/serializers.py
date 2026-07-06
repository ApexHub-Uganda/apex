from rest_framework import serializers

from apps.core.email_validation import validate_deliverable_email
from apps.events.models import Event, EventRegistration

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class EventSerializer(serializers.ModelSerializer):
    registration_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_registration_count(self, obj) -> int:
        return obj.registrations.count()


class EventRegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)

    class Meta:
        model = EventRegistration
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs: dict) -> dict:
        email = attrs.get(
            "registrant_email",
            getattr(self.instance, "registrant_email", "") if self.instance else "",
        )
        if email:
            error = validate_deliverable_email(email, required=False)
            if error:
                raise serializers.ValidationError({"registrant_email": error})
        return attrs