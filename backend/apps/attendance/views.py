from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.mixins import AcademicScopeMixin
from apps.attendance.models import AttendanceRecord, LessonAttendanceEntry, LessonAttendanceSession
from apps.attendance.serializers import (
    AttendanceRecordSerializer,
    LessonAttendanceEntrySerializer,
    LessonAttendanceSessionSerializer,
)
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.students.models import Student


class AttendanceRecordViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "student_attendance"
    queryset = AttendanceRecord.objects.select_related("student", "staff", "marked_by")
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["attendee_type", "status", "date", "student", "staff"]
    ordering_fields = ["date"]


class LessonAttendanceSessionViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "lesson_attendance"
    queryset = LessonAttendanceSession.objects.select_related(
        "school_class", "subject", "teacher", "teacher__staff", "timetable",
    )
    serializer_class = LessonAttendanceSessionSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "subject", "teacher", "date", "status"]
    ordering_fields = ["date"]


class LessonAttendanceEntryViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "lesson_attendance"
    queryset = LessonAttendanceEntry.objects.select_related("session", "student")
    serializer_class = LessonAttendanceEntrySerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["session", "student", "status"]


class LessonAttendanceBulkView(APIView):
    """Create or update attendance entries for all students in a class session."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("lesson_attendance")())
        return perms

    def post(self, request):
        from apps.academics.scoping import filter_queryset_for_user

        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.data.get("session")
        school_class_id = request.data.get("school_class")
        subject_id = request.data.get("subject")
        session_date = request.data.get("date")
        entries = request.data.get("entries") or []

        if session_id:
            session = LessonAttendanceSession.objects.filter(
                tenant=tenant, pk=session_id, is_deleted=False,
            ).first()
            if session is None:
                return Response(
                    {"success": False, "message": "Session not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            scoped = filter_queryset_for_user(
                LessonAttendanceSession.objects.filter(pk=session.pk),
                request.user,
            )
            if not scoped.exists():
                return Response(
                    {"success": False, "message": "You do not have access to this session."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            if not school_class_id or not subject_id or not session_date:
                return Response(
                    {"success": False, "message": "session or (school_class, subject, date) required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.academics.scoping import user_can_access_class

            if not user_can_access_class(request.user, school_class_id):
                return Response(
                    {"success": False, "message": "You do not have access to this class."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            teacher = getattr(
                getattr(request.user, "staff_profile", None), "teacher_profile", None,
            )
            session = LessonAttendanceSession.objects.create(
                tenant=tenant,
                school_class_id=school_class_id,
                subject_id=subject_id,
                teacher=teacher,
                date=session_date,
                created_by=request.user,
                updated_by=request.user,
            )

        saved = 0
        for row in entries:
            student_id = row.get("student")
            if not student_id:
                continue
            if not Student.objects.filter(
                tenant=tenant, pk=student_id, school_class_id=session.school_class_id,
            ).exists():
                continue
            LessonAttendanceEntry.objects.update_or_create(
                tenant=tenant,
                session=session,
                student_id=student_id,
                defaults={
                    "status": row.get("status") or "present",
                    "remarks": (row.get("remarks") or "").strip(),
                    "updated_by": request.user,
                },
            )
            saved += 1

        return Response({
            "success": True,
            "message": f"Saved {saved} attendance record(s).",
            "data": {
                "session": LessonAttendanceSessionSerializer(session).data,
                "saved": saved,
            },
        })
