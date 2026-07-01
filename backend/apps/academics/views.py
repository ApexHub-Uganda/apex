from apps.academics.models import AcademicYear, Assignment, Class, Department, Homework, Stream, Subject, Term, Timetable
from apps.academics.serializers import (
    AcademicYearSerializer, AssignmentSerializer, ClassSerializer, DepartmentSerializer,
    HomeworkSerializer, StreamSerializer, SubjectSerializer, TermSerializer, TimetableSerializer,
)
from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet


class AcademicYearViewSet(BaseModelViewSet):
    required_feature_key = "academic_years"
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["is_current"]
    search_fields = ["name"]


class TermViewSet(BaseModelViewSet):
    required_feature_key = "terms"
    queryset = Term.objects.select_related("academic_year")
    serializer_class = TermSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year", "is_current"]


class DepartmentViewSet(BaseModelViewSet):
    required_feature_key = "departments"
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code"]


class ClassViewSet(BaseModelViewSet):
    required_feature_key = "classes"
    queryset = Class.objects.select_related("academic_year", "class_teacher")
    serializer_class = ClassSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year"]
    search_fields = ["name", "code"]


class StreamViewSet(BaseModelViewSet):
    required_feature_key = "streams"
    queryset = Stream.objects.select_related("school_class")
    serializer_class = StreamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class"]


class SubjectViewSet(BaseModelViewSet):
    required_feature_key = "subjects"
    queryset = Subject.objects.select_related("department")
    serializer_class = SubjectSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code"]
    filterset_fields = ["department", "is_compulsory"]


class TimetableViewSet(BaseModelViewSet):
    required_feature_key = "timetables"
    queryset = Timetable.objects.select_related("school_class", "subject", "teacher")
    serializer_class = TimetableSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "day_of_week", "subject"]


class AssignmentViewSet(BaseModelViewSet):
    required_feature_key = "subject_assignment"
    queryset = Assignment.objects.select_related("subject", "school_class", "teacher")
    serializer_class = AssignmentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "subject"]
    search_fields = ["title"]


class HomeworkViewSet(BaseModelViewSet):
    required_feature_key = "homework"
    queryset = Homework.objects.select_related("subject", "school_class", "teacher")
    serializer_class = HomeworkSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "subject", "is_published"]
    search_fields = ["title"]