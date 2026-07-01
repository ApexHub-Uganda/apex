from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.hostel.models import Allocation, Hostel, Room
from apps.hostel.serializers import AllocationSerializer, HostelSerializer, RoomSerializer

class HostelViewSet(BaseModelViewSet):
    required_feature_key = "hostel_management"
    queryset = Hostel.objects.select_related("warden")
    serializer_class = HostelSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]

class RoomViewSet(BaseModelViewSet):
    required_feature_key = "rooms"
    queryset = Room.objects.select_related("hostel")
    serializer_class = RoomSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["hostel", "is_available"]

class AllocationViewSet(BaseModelViewSet):
    required_feature_key = "room_allocation"
    queryset = Allocation.objects.select_related("student", "room")
    serializer_class = AllocationSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "student", "room"]
