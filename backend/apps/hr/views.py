from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.hr.models import Leave, PerformanceReview
from apps.hr.serializers import LeaveSerializer, PerformanceReviewSerializer

class LeaveViewSet(BaseModelViewSet):
    required_feature_key = "leave_requests"
    queryset = Leave.objects.select_related("staff", "approved_by")
    serializer_class = LeaveSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["staff", "status", "leave_type"]

class PerformanceReviewViewSet(BaseModelViewSet):
    required_feature_key = "performance_reviews"
    queryset = PerformanceReview.objects.select_related("staff", "reviewer")
    serializer_class = PerformanceReviewSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["staff", "status"]
