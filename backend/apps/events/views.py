from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.events.models import Event, EventRegistration
from apps.events.serializers import EventRegistrationSerializer, EventSerializer


class EventViewSet(BaseModelViewSet):
    required_feature_key = "event_management"
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "target_audience"]
    search_fields = ["title", "location"]


class EventRegistrationViewSet(BaseModelViewSet):
    required_feature_key = "event_registration"
    queryset = EventRegistration.objects.select_related("event", "student")
    serializer_class = EventRegistrationSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["event", "status", "student"]
    search_fields = ["registrant_name", "registrant_email"]