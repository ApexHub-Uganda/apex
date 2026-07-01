from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.transport.models import Driver, Route, StudentTransport, Vehicle
from apps.transport.serializers import DriverSerializer, RouteSerializer, StudentTransportSerializer, VehicleSerializer

class VehicleViewSet(BaseModelViewSet):
    required_feature_key = "vehicles"
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "vehicle_type"]

class DriverViewSet(BaseModelViewSet):
    required_feature_key = "vehicles"
    queryset = Driver.objects.select_related("staff")
    serializer_class = DriverSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]

class RouteViewSet(BaseModelViewSet):
    required_feature_key = "routes"
    queryset = Route.objects.select_related("vehicle", "driver")
    serializer_class = RouteSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]

class StudentTransportViewSet(BaseModelViewSet):
    required_feature_key = "student_transport_assignment"
    queryset = StudentTransport.objects.select_related("student", "route")
    serializer_class = StudentTransportSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "route", "student"]
