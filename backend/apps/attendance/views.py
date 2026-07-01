from apps.attendance.models import AttendanceRecord
from apps.attendance.serializers import AttendanceRecordSerializer
from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet

class AttendanceRecordViewSet(BaseModelViewSet):
    required_feature_key = "student_attendance"
    queryset = AttendanceRecord.objects.select_related("student", "staff", "marked_by")
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["attendee_type", "status", "date", "student", "staff"]
    ordering_fields = ["date"]
