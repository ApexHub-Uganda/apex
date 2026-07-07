from apps.academics.models import (
    AcademicYear,
    Assignment,
    Class,
    ClassNotice,
    Classroom,
    Department,
    DisciplineRemark,
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
    ClassNoticeSerializer,
    ClassSerializer,
    ClassroomSerializer,
    DepartmentSerializer,
    DisciplineRemarkSerializer,
    HomeworkSerializer,
    PeriodSerializer,
    StreamSerializer,
    SubjectPaperSerializer,
    SubjectSerializer,
    TermSerializer,
    TimetableSerializer,
)
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.mixins import AcademicScopeMixin
from apps.academics.workspaces import build_academic_workspace
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet


class AcademicYearViewSet(AcademicScopeMixin, BaseModelViewSet):
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


class ClassViewSet(AcademicScopeMixin, BaseModelViewSet):
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


class StreamViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "streams"
    queryset = Stream.objects.select_related("school_class")
    serializer_class = StreamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class"]


class SubjectViewSet(AcademicScopeMixin, BaseModelViewSet):
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


class SubjectPaperViewSet(AcademicScopeMixin, BaseModelViewSet):
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


class TimetableViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "timetables"
    queryset = Timetable.objects.select_related("school_class", "subject", "teacher")
    serializer_class = TimetableSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "day_of_week", "subject"]


class AssignmentViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "subject_assignment"
    queryset = Assignment.objects.select_related("subject", "school_class", "teacher")
    serializer_class = AssignmentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "subject"]
    search_fields = ["title"]


class HomeworkViewSet(AcademicScopeMixin, BaseModelViewSet):
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


class AcademicWorkspaceView(APIView):
    """Role workspace summary for teacher, HoD, DoS, and class teacher."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresAnyFeature(
            "teacher_workspace", "hod_workspace", "dos_workspace", "class_teacher_tools",
        )())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        return Response({
            "success": True,
            "data": build_academic_workspace(tenant=tenant, user=request.user),
        })


class ClassNoticeViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "class_notices"
    queryset = ClassNotice.objects.select_related("school_class", "author", "author__staff")
    serializer_class = ClassNoticeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "is_published"]
    search_fields = ["title", "body"]

    def perform_create(self, serializer):
        teacher = getattr(getattr(self.request.user, "staff_profile", None), "teacher_profile", None)
        serializer.save(author=teacher, created_by=self.request.user, updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        notice = self.get_object()
        notice.is_published = True
        notice.published_at = timezone.now()
        notice.updated_by = request.user
        notice.save(update_fields=["is_published", "published_at", "updated_by", "updated_at"])
        return Response({
            "success": True,
            "message": "Notice published.",
            "data": ClassNoticeSerializer(notice).data,
        })


class DisciplineRemarkViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "discipline_remarks"
    queryset = DisciplineRemark.objects.select_related(
        "student", "school_class", "subject", "term", "recorded_by", "recorded_by__staff",
    )
    serializer_class = DisciplineRemarkSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "student", "subject", "term", "remark_type"]
    search_fields = ["title", "description", "student__first_name", "student__last_name"]

    def perform_create(self, serializer):
        teacher = getattr(getattr(self.request.user, "staff_profile", None), "teacher_profile", None)
        serializer.save(recorded_by=teacher, created_by=self.request.user, updated_by=self.request.user)