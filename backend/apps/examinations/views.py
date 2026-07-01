from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.examinations.models import Exam, Grade, GradingScale, ReportCard
from apps.examinations.serializers import ExamSerializer, GradeSerializer, GradingScaleSerializer, ReportCardSerializer

class GradingScaleViewSet(BaseModelViewSet):
    required_feature_key = "grade_calculation"
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]

class ExamViewSet(BaseModelViewSet):
    required_feature_key = "examination_management"
    queryset = Exam.objects.select_related("subject", "school_class", "term")
    serializer_class = ExamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "term", "subject", "exam_type"]

class GradeViewSet(BaseModelViewSet):
    required_feature_key = "marks_entry"
    queryset = Grade.objects.select_related("exam", "student", "graded_by")
    serializer_class = GradeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["exam", "student"]

class ReportCardViewSet(BaseModelViewSet):
    required_feature_key = "report_cards"
    queryset = ReportCard.objects.select_related("student", "term", "school_class")
    serializer_class = ReportCardSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "term", "school_class", "is_published"]
