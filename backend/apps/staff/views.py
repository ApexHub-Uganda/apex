from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.staff.models import Staff, Teacher
from apps.staff.serializers import StaffSerializer, TeacherSerializer

class StaffViewSet(BaseModelViewSet):
    required_feature_key = "staff_management"
    queryset = Staff.objects.select_related("department")
    serializer_class = StaffSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "department", "employment_type"]
    search_fields = ["first_name", "last_name", "employee_id", "email"]

class TeacherViewSet(BaseModelViewSet):
    required_feature_key = "staff_management"
    queryset = Teacher.objects.select_related("staff").prefetch_related("subjects")
    serializer_class = TeacherSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["is_class_teacher"]
    search_fields = ["staff__first_name", "staff__last_name"]
