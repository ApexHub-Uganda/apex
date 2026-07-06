from apps.academics.models import (
    AcademicYear,
    Assignment,
    Class,
    Classroom,
    Department,
    Homework,
    Period,
    Stream,
    Subject,
    SubjectPaper,
    Term,
    Timetable,
)
from apps.academics.serializers import (
    AcademicYearSerializer,
    AssignmentSerializer,
    ClassSerializer,
    ClassroomSerializer,
    DepartmentSerializer,
    HomeworkSerializer,
    PeriodSerializer,
    StreamSerializer,
    SubjectPaperSerializer,
    SubjectSerializer,
    TermSerializer,
    TimetableSerializer,
)
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
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

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve"):
            perms.append(
                RequiresAnyFeature("terms", "examination_management", "marks_entry", "academic_years")(),
            )
        else:
            perms.append(RequiresFeature("terms")())
        return perms


class DepartmentViewSet(BaseModelViewSet):
    """Departments are shared by Core Management, Academics, and HR modules."""

    required_feature_key = None
    queryset = Department.objects.select_related("head")
    serializer_class = DepartmentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code"]

    def get_permissions(self):
        from apps.core.permissions import RequiresAnyFeature

        perms = [permission() for permission in self.permission_classes]
        perms.append(RequiresAnyFeature("departments", "hr_departments")())
        return perms


class ClassViewSet(BaseModelViewSet):
    required_feature_key = "classes"
    queryset = Class.objects.select_related("academic_year", "class_teacher")
    serializer_class = ClassSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year"]
    search_fields = ["name", "code"]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve"):
            perms.append(
                RequiresAnyFeature(
                    "classes", "examination_management", "marks_entry",
                    "student_management", "subject_assignment", "homework", "timetables",
                )(),
            )
        else:
            perms.append(RequiresFeature("classes")())
        return perms


class StreamViewSet(BaseModelViewSet):
    required_feature_key = "streams"
    queryset = Stream.objects.select_related("school_class")
    serializer_class = StreamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class"]


class SubjectViewSet(BaseModelViewSet):
    required_feature_key = "subjects"
    queryset = Subject.objects.select_related("department").prefetch_related("papers")
    serializer_class = SubjectSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code"]
    filterset_fields = ["department", "is_compulsory"]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve"):
            perms.append(
                RequiresAnyFeature(
                    "subjects", "examination_management", "marks_entry",
                    "subject_assignment", "homework", "timetables",
                )(),
            )
        else:
            perms.append(RequiresFeature("subjects")())
        return perms


class SubjectPaperViewSet(BaseModelViewSet):
    required_feature_key = "subjects"
    queryset = SubjectPaper.objects.select_related("subject")
    serializer_class = SubjectPaperSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["subject"]
    search_fields = ["code", "name"]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve"):
            perms.append(
                RequiresAnyFeature("subjects", "examination_management", "marks_entry")(),
            )
        else:
            perms.append(RequiresFeature("subjects")())
        return perms


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


class PeriodViewSet(BaseModelViewSet):
    required_feature_key = "periods"
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    ordering_fields = ["sort_order", "start_time"]


class ClassroomViewSet(BaseModelViewSet):
    required_feature_key = "classrooms"
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code", "building"]
    filterset_fields = ["room_type", "is_available"]