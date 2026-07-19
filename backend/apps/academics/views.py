from apps.academics.class_hub import (
    build_class_deletion_preview,
    build_class_hub_detail,
    build_class_overview_row,
    classes_overview_queryset,
    soft_delete_class_graph,
    user_can_manage_class_prefects,
    user_can_write_classes,
)
from apps.academics.models import (
    AcademicYear,
    Assignment,
    Class,
    ClassNotice,
    ClassPrefect,
    Classroom,
    Department,
    DisciplineRemark,
    Homework,
    Period,
    Stream,
    Subject,
    SubjectPaper,
    TeachingAssignment,
    Term,
    Timetable,
)
from apps.academics.serializers import (
    AcademicYearSerializer,
    AssignmentSerializer,
    ClassNoticeSerializer,
    ClassPrefectSerializer,
    ClassSerializer,
    ClassroomSerializer,
    DepartmentSerializer,
    DisciplineRemarkSerializer,
    HomeworkSerializer,
    PeriodSerializer,
    StreamSerializer,
    SubjectPaperSerializer,
    SubjectSerializer,
    TeachingAssignmentBulkSerializer,
    TeachingAssignmentSerializer,
    TeachingAssignmentTeacherSyncSerializer,
    TermSerializer,
    TimetableSerializer,
)
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.mixins import (
    AcademicScopeMixin,
    AcademicYearSingletonMixin,
    TermSingletonMixin,
    TimetableActiveTermMixin,
)
from apps.academics.workspaces import build_academic_workspace
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet


class AcademicYearViewSet(AcademicYearSingletonMixin, AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "academic_years"
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["is_current"]
    search_fields = ["name"]


class TermViewSet(TermSingletonMixin, AcademicScopeMixin, BaseModelViewSet):
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


class DepartmentViewSet(AcademicScopeMixin, BaseModelViewSet):
    """Departments are shared by Core Management, Academics, and HR modules."""

    required_feature_key = None
    academic_scope_feature = "departments"
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
    queryset = Class.objects.select_related(
        "academic_year", "class_teacher", "class_teacher__staff",
    )
    serializer_class = ClassSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year", "level_type", "curriculum"]
    search_fields = ["name", "code", "section", "room"]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        action = getattr(self, "action", None)
        request = getattr(self, "request", None)
        read_actions = ("list", "retrieve", "form_options", "overview", "hub", "deletion_preview")
        prefect_actions = ("prefects", "remove_prefect")

        if action in read_actions or (action == "prefects" and request and request.method == "GET"):
            perms.append(
                RequiresAnyFeature(
                    "classes", "examination_management", "marks_entry",
                    "student_management", "subject_assignment", "homework", "timetables",
                )(),
            )
        elif action in prefect_actions:
            perms.append(RequiresAnyFeature("classes", "class_teacher_tools")())
        else:
            perms.append(RequiresFeature("classes")())
        return perms

    @action(detail=False, methods=["get"], url_path="form-options")
    def form_options(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"teachers": [], "academic_years": []}})

        from apps.staff.models import Teacher

        teachers = Teacher.objects.filter(
            tenant=tenant,
            is_deleted=False,
            staff__is_deleted=False,
            staff__status="active",
        ).select_related("staff").order_by("staff__first_name", "staff__last_name")

        years = AcademicYear.objects.filter(tenant=tenant, is_deleted=False).order_by("-start_date")

        return Response({
            "success": True,
            "data": {
                "teachers": [
                    {"value": str(t.id), "label": t.staff.full_name}
                    for t in teachers
                ],
                "academic_years": [
                    {
                        "value": str(y.id),
                        "label": y.name,
                        "is_current": y.is_current,
                    }
                    for y in years
                ],
            },
        })

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": []})

        queryset = self.filter_queryset(classes_overview_queryset(tenant))
        rows = [build_class_overview_row(school_class) for school_class in queryset]
        return Response({"success": True, "data": rows})

    def destroy(self, request, *args, **kwargs):
        school_class = self.get_object()
        if not user_can_write_classes(request.user):
            return Response(
                {"success": False, "message": "You do not have permission to delete classes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        preview = build_class_deletion_preview(school_class, user=request.user)
        if preview["blockers"]:
            return Response(
                {
                    "success": False,
                    "message": preview["blockers"][0],
                    "data": preview,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        soft_delete_class_graph(school_class, user=request.user)
        return Response(
            {"success": True, "message": f"Class '{school_class.name}' deleted."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="deletion-preview")
    def deletion_preview(self, request, pk=None):
        school_class = self.get_object()
        preview = build_class_deletion_preview(school_class, user=request.user)
        return Response({"success": True, "data": preview})

    @action(detail=True, methods=["get"], url_path="hub")
    def hub(self, request, pk=None):
        school_class = self.get_object()
        tenant = request.user.tenant
        stream_id = request.query_params.get("stream") or None
        payload = build_class_hub_detail(
            school_class,
            tenant=tenant,
            user=request.user,
            stream_id=stream_id,
        )
        return Response({"success": True, "data": payload})

    @action(detail=True, methods=["get", "post"], url_path="prefects")
    def prefects(self, request, pk=None):
        school_class = self.get_object()
        tenant = request.user.tenant

        if request.method == "GET":
            prefects = ClassPrefect.objects.filter(
                tenant=tenant,
                school_class=school_class,
                is_deleted=False,
            ).select_related("student", "stream")
            stream_id = request.query_params.get("stream")
            if stream_id:
                prefects = prefects.filter(Q(stream_id=stream_id) | Q(stream__isnull=True))
            serializer = ClassPrefectSerializer(prefects, many=True, context={"request": request})
            return Response({"success": True, "data": serializer.data})

        if not user_can_manage_class_prefects(request.user, school_class):
            return Response(
                {"success": False, "message": "You do not have permission to appoint class prefects."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = {
            **request.data,
            "school_class": str(school_class.id),
        }
        serializer = ClassPrefectSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(
            tenant=tenant,
            appointed_by=request.user,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            {"success": True, "message": "Class prefect appointed.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="prefects/remove")
    def remove_prefect(self, request, pk=None):
        school_class = self.get_object()
        tenant = request.user.tenant

        if not user_can_manage_class_prefects(request.user, school_class):
            return Response(
                {"success": False, "message": "You do not have permission to remove class prefects."},
                status=status.HTTP_403_FORBIDDEN,
            )

        prefect_id = request.data.get("prefect_id")
        if not prefect_id:
            return Response(
                {"success": False, "message": "prefect_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prefect = ClassPrefect.objects.filter(
            tenant=tenant,
            school_class=school_class,
            id=prefect_id,
            is_deleted=False,
        ).first()
        if prefect is None:
            return Response(
                {"success": False, "message": "Prefect not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        prefect.is_deleted = True
        prefect.updated_by = request.user
        prefect.save(update_fields=["is_deleted", "updated_by", "updated_at"])
        return Response({"success": True, "message": "Class prefect removed."})


class StreamViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "classes"
    queryset = Stream.objects.select_related("school_class", "school_class__academic_year")
    serializer_class = StreamSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class"]
    search_fields = ["name", "school_class__name", "school_class__code"]

    def destroy(self, request, *args, **kwargs):
        stream = self.get_object()
        if not user_can_write_classes(request.user):
            return Response(
                {"success": False, "message": "You do not have permission to delete streams."},
                status=status.HTTP_403_FORBIDDEN,
            )

        active_students = stream.students.filter(is_deleted=False, status="active").count()
        if active_students:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"Cannot delete stream '{stream.name}' while "
                        f"{active_students} active student(s) remain assigned."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stream.soft_delete(user=request.user)
        ClassPrefect.objects.filter(
            tenant=stream.tenant,
            stream=stream,
            is_deleted=False,
        ).update(is_deleted=True, updated_by=request.user)
        return Response(
            {"success": True, "message": f"Stream '{stream.name}' deleted."},
            status=status.HTTP_200_OK,
        )

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        if getattr(self, "action", None) in ("list", "retrieve", "form_options"):
            perms.append(
                RequiresAnyFeature("classes", "student_management")(),
            )
        else:
            perms.append(RequiresFeature("classes")())
        return perms

    @action(detail=False, methods=["get"], url_path="form-options")
    def form_options(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"classes": []}})

        classes = Class.objects.filter(tenant=tenant, is_deleted=False).select_related(
            "academic_year",
        ).order_by("name")

        return Response({
            "success": True,
            "data": {
                "classes": [
                    {
                        "value": str(c.id),
                        "label": f"{c.name} ({c.code})",
                        "academic_year_name": c.academic_year.name if c.academic_year_id else "",
                    }
                    for c in classes
                ],
            },
        })


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


class TimetableViewSet(TimetableActiveTermMixin, AcademicScopeMixin, BaseModelViewSet):
    """
    List/filter timetable slots.
    Teachers see their periods from *published* schedules only.
    Admins / DoS see full school data (including drafts).
    """
    required_feature_key = "timetables"
    queryset = Timetable.objects.select_related(
        "school_class", "subject", "teacher__staff", "period", "stream", "schedule",
    )
    serializer_class = TimetableSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = [
        "school_class", "day_of_week", "subject", "schedule", "schedule_type",
        "term", "examination_session", "stream", "teacher", "is_break_slot",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin
        if user_is_school_admin(user):
            return qs
        can_write = user_can_access_feature(
            getattr(user, "tenant", None), user, "timetables", require_write=True,
        )
        if not can_write:
            # Published only for read-only (teachers)
            qs = qs.filter(
                schedule__status__in=["published", "active"],
                schedule__is_deleted=False,
            )
        return qs

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        perms.append(RequiresFeature("timetables")())
        return perms

    def perform_create(self, serializer):
        from apps.academics.timetable_generator import assert_timetable_write

        assert_timetable_write(self.request.user)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        from apps.academics.timetable_generator import (
            assert_timetable_admin_lock,
            schedule_is_locked_for_user,
        )

        instance = self.get_object()
        if schedule_is_locked_for_user(instance.schedule, self.request.user):
            assert_timetable_admin_lock(self.request.user)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        from apps.academics.timetable_generator import (
            assert_timetable_admin_lock,
            schedule_is_locked_for_user,
        )

        if schedule_is_locked_for_user(instance.schedule, self.request.user):
            assert_timetable_admin_lock(self.request.user)
        super().perform_destroy(instance)


class TeachingAssignmentViewSet(AcademicScopeMixin, BaseModelViewSet):
    """Assign teachers to subjects and classes — gated by subject_assignment / teacher_assignments."""

    required_feature_key = "subject_assignment"
    academic_scope_feature = "subject_assignment"
    queryset = TeachingAssignment.objects.select_related(
        "teacher__staff",
        "school_class",
        "school_class__academic_year",
        "subject",
        "academic_year",
    )
    serializer_class = TeachingAssignmentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["teacher", "school_class", "subject", "academic_year", "is_active"]
    search_fields = [
        "teacher__staff__first_name",
        "teacher__staff__last_name",
        "school_class__name",
        "school_class__code",
        "subject__name",
        "subject__code",
    ]

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        perms.append(RequiresAnyFeature("subject_assignment", "teacher_assignments")())
        return perms

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        from apps.academics.teaching_assignments import sync_teacher_subjects_from_assignments
        sync_teacher_subjects_from_assignments(instance.teacher)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        from apps.academics.teaching_assignments import sync_teacher_subjects_from_assignments
        sync_teacher_subjects_from_assignments(instance.teacher)

    def perform_destroy(self, instance):
        teacher = instance.teacher
        super().perform_destroy(instance)
        from apps.academics.teaching_assignments import sync_teacher_subjects_from_assignments
        sync_teacher_subjects_from_assignments(teacher)

    @action(detail=False, methods=["get"], url_path="form-options")
    def form_options(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"teachers": [], "classes": [], "subjects": []}})

        from apps.staff.models import Teacher as TeacherModel

        teachers = TeacherModel.objects.filter(
            tenant=tenant,
            is_deleted=False,
            staff__is_deleted=False,
            staff__status="active",
        ).select_related("staff").order_by("staff__first_name", "staff__last_name")

        classes = Class.objects.filter(
            tenant=tenant,
            is_deleted=False,
        ).select_related("academic_year").order_by("name")

        subjects = Subject.objects.filter(
            tenant=tenant,
            is_deleted=False,
        ).order_by("code")

        return Response({
            "success": True,
            "data": {
                "teachers": [
                    {
                        "value": str(t.id),
                        "label": t.staff.full_name,
                        "designation": t.staff.designation or "",
                    }
                    for t in teachers
                ],
                "classes": [
                    {
                        "value": str(c.id),
                        "label": f"{c.name} ({c.code})",
                        "academic_year": str(c.academic_year_id),
                        "academic_year_name": c.academic_year.name,
                    }
                    for c in classes
                ],
                "subjects": [
                    {
                        "value": str(s.id),
                        "label": s.code,
                        "code": s.code,
                        "name": s.name,
                    }
                    for s in subjects
                ],
            },
        })

    def _resolve_teaching_assignment_targets(self, request, data: dict):
        tenant = request.user.tenant
        from apps.staff.models import Teacher as TeacherModel

        teacher = TeacherModel.objects.filter(pk=data["teacher"], tenant=tenant, is_deleted=False).first()
        school_class = Class.objects.filter(pk=data["school_class"], tenant=tenant, is_deleted=False).first()
        if teacher is None or school_class is None:
            return None, None, None, None, Response(
                {"success": False, "message": "Teacher or class not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subject_ids = data["subject_ids"]
        subjects = list(
            Subject.objects.filter(tenant=tenant, id__in=subject_ids, is_deleted=False).order_by("code"),
        )
        if len(subjects) != len(set(subject_ids)):
            return None, None, None, None, Response(
                {"success": False, "message": "One or more subjects were not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return tenant, teacher, school_class, subjects, None

    @action(detail=False, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request):
        serializer = TeachingAssignmentBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant, teacher, school_class, subjects, error_response = self._resolve_teaching_assignment_targets(
            request, serializer.validated_data,
        )
        if error_response is not None:
            return error_response
        notes = serializer.validated_data.get("notes", "")

        from apps.academics.teaching_assignments import upsert_teaching_assignment, sync_teacher_subjects_from_assignments

        created = []
        skipped = 0
        for subject in subjects:
            row, upsert_status = upsert_teaching_assignment(
                tenant=tenant,
                teacher=teacher,
                school_class=school_class,
                subject=subject,
                notes=notes,
                user=request.user,
            )
            if upsert_status in ("created", "restored"):
                created.append(row)
            else:
                skipped += 1

        sync_teacher_subjects_from_assignments(teacher)

        payload = TeachingAssignmentSerializer(created, many=True).data
        return Response({
            "success": True,
            "message": f"{len(created)} assignment(s) created." + (f" {skipped} already existed." if skipped else ""),
            "data": payload,
            "created_count": len(created),
            "skipped_count": skipped,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="sync-assign")
    def sync_assign(self, request):
        """Set the full subject list for a teacher + class staffing group."""
        serializer = TeachingAssignmentBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant, teacher, school_class, subjects, error_response = self._resolve_teaching_assignment_targets(
            request, serializer.validated_data,
        )
        if error_response is not None:
            return error_response
        notes = serializer.validated_data.get("notes", "")

        from apps.academics.teaching_assignments import sync_teacher_class_subjects

        counts = sync_teacher_class_subjects(
            tenant=tenant,
            teacher=teacher,
            school_class=school_class,
            subjects=subjects,
            notes=notes,
            user=request.user,
        )
        rows = TeachingAssignment.objects.filter(
            tenant=tenant,
            teacher=teacher,
            school_class=school_class,
            is_active=True,
            is_deleted=False,
        ).select_related(
            "teacher__staff",
            "school_class",
            "school_class__academic_year",
            "subject",
            "academic_year",
        )
        payload = TeachingAssignmentSerializer(rows, many=True).data
        parts = []
        if counts["created_count"]:
            parts.append(f"{counts['created_count']} added")
        if counts["restored_count"]:
            parts.append(f"{counts['restored_count']} restored")
        if counts["removed_count"]:
            parts.append(f"{counts['removed_count']} removed")
        if counts["updated_count"]:
            parts.append(f"{counts['updated_count']} updated")
        message = "Assignment saved." if not parts else f"Assignment saved ({', '.join(parts)})."
        return Response({
            "success": True,
            "message": message,
            "data": payload,
            **counts,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="sync-teacher")
    def sync_teacher(self, request):
        """Set the full class–subject assignment list for one teacher."""
        serializer = TeachingAssignmentTeacherSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = request.user.tenant
        data = serializer.validated_data
        notes = data.get("notes", "")

        from apps.staff.models import Teacher as TeacherModel
        from apps.academics.teaching_assignments import sync_teacher_assignments

        teacher = TeacherModel.objects.filter(
            pk=data["teacher"], tenant=tenant, is_deleted=False,
        ).first()
        if teacher is None:
            return Response(
                {"success": False, "message": "Teacher not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        class_ids = {entry["school_class"] for entry in data["assignments"]}
        subject_ids = {entry["subject"] for entry in data["assignments"]}
        classes = {
            row.id: row
            for row in Class.objects.filter(tenant=tenant, id__in=class_ids, is_deleted=False)
        }
        subject_map = {
            row.id: row
            for row in Subject.objects.filter(tenant=tenant, id__in=subject_ids, is_deleted=False)
        }
        if len(classes) != len(class_ids) or len(subject_map) != len(subject_ids):
            return Response(
                {"success": False, "message": "One or more classes or subjects were not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pairs: list[tuple[Class, Subject]] = []
        for entry in data["assignments"]:
            school_class = classes[entry["school_class"]]
            subject = subject_map[entry["subject"]]
            if school_class.tenant_id != teacher.tenant_id or subject.tenant_id != teacher.tenant_id:
                return Response(
                    {"success": False, "message": "Teacher, class, and subject must belong to the same school."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pairs.append((school_class, subject))

        counts = sync_teacher_assignments(
            tenant=tenant,
            teacher=teacher,
            pairs=pairs,
            notes=notes,
            user=request.user,
        )
        rows = TeachingAssignment.objects.filter(
            tenant=tenant,
            teacher=teacher,
            is_active=True,
            is_deleted=False,
        ).select_related(
            "teacher__staff",
            "school_class",
            "school_class__academic_year",
            "subject",
            "academic_year",
        ).order_by("school_class__name", "subject__code")
        payload = TeachingAssignmentSerializer(rows, many=True).data
        parts = []
        if counts["created_count"]:
            parts.append(f"{counts['created_count']} added")
        if counts["restored_count"]:
            parts.append(f"{counts['restored_count']} restored")
        if counts["removed_count"]:
            parts.append(f"{counts['removed_count']} removed")
        if counts["updated_count"]:
            parts.append(f"{counts['updated_count']} updated")
        message = "Assignments saved." if not parts else f"Assignments saved ({', '.join(parts)})."
        return Response({
            "success": True,
            "message": message,
            "data": payload,
            **counts,
        }, status=status.HTTP_200_OK)


class AssignmentViewSet(AcademicScopeMixin, BaseModelViewSet):
    required_feature_key = "assignments"
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

    def get_queryset(self):
        """
        Admins / school-wide roles see the full bell schedule.
        Subject teachers see only periods that appear on *their* timetable rows
        (my periods). Write operations still require periods feature write.
        """
        qs = super().get_queryset()
        user = self.request.user
        from apps.academics.scoping import get_academic_context, user_has_school_wide_academic_access
        from apps.tenants.role_permissions import user_is_school_admin

        if user_is_school_admin(user) or user_has_school_wide_academic_access(user):
            return qs
        ctx = get_academic_context(user)
        if ctx is None or ctx.teacher is None:
            return qs.none()
        # Periods used by this teacher's assigned slots
        period_ids = (
            Timetable.objects.filter(
                tenant=user.tenant,
                teacher=ctx.teacher,
                is_deleted=False,
                period__isnull=False,
            )
            .values_list("period_id", flat=True)
            .distinct()
        )
        return qs.filter(pk__in=period_ids)


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