from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student
from apps.students.serializers import (
    AdmissionSerializer, GuardianSerializer, MedicalRecordSerializer, ParentSerializer, StudentSerializer,
)


class ParentViewSet(BaseModelViewSet):
    required_feature_key = "parent_management"
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["first_name", "last_name", "email", "phone"]


class StudentViewSet(BaseModelViewSet):
    required_feature_key = "student_management"
    queryset = Student.objects.select_related("school_class", "stream")
    serializer_class = StudentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "school_class", "stream", "gender"]
    search_fields = ["first_name", "last_name", "admission_number", "email"]

    @action(detail=True, methods=["post"])
    def enroll(self, request: Request, pk: str = None) -> Response:
        student = self.get_object()
        class_id = request.data.get("school_class")
        stream_id = request.data.get("stream")
        if class_id:
            student.school_class_id = class_id
        if stream_id:
            student.stream_id = stream_id
        student.status = "active"
        student.save()
        return Response(StudentSerializer(student).data)


class GuardianViewSet(BaseModelViewSet):
    required_feature_key = "parent_management"
    queryset = Guardian.objects.select_related("student")
    serializer_class = GuardianSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "is_primary"]


class AdmissionViewSet(BaseModelViewSet):
    required_feature_key = "admissions"
    queryset = Admission.objects.select_related("student")
    serializer_class = AdmissionSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]


class MedicalRecordViewSet(BaseModelViewSet):
    required_feature_key = "medical_records"
    queryset = MedicalRecord.objects.select_related("student")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "is_chronic"]