from rest_framework import serializers

from apps.staff.models import Teacher
from apps.academics.models import (
    AcademicYear,
    AssessmentScheme,
    Assignment,
    Class,
    ClassNotice,
    ClassPrefect,
    Classroom,
    Department,
    DisciplineRemark,
    Homework,
    HomeworkSubmission,
    Period,
    Stream,
    StudentSubjectRegistration,
    Subject,
    SubjectCombination,
    SubjectPaper,
    TeachingAssignment,
    Term,
    Timetable,
    TimetableSchedule,
)

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs: dict) -> dict:
        if self.instance is None:
            from apps.academics.singleton import assert_can_create_academic_year

            request = self.context.get("request")
            tenant = getattr(request.user, "tenant", None) if request else None
            if tenant is not None:
                assert_can_create_academic_year(tenant)
        return attrs


class TermSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs: dict) -> dict:
        if self.instance is None:
            from apps.academics.singleton import assert_can_create_term

            request = self.context.get("request")
            tenant = getattr(request.user, "tenant", None) if request else None
            if tenant is not None:
                assert_can_create_term(tenant)
        return attrs


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_head_name(self, obj) -> str | None:
        return obj.head.full_name if obj.head_id else None

    def validate(self, attrs: dict) -> dict:
        if attrs.get("head") == "":
            attrs["head"] = None
        return attrs


class ClassSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    class_teacher_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    class_teacher = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.none(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Class
        fields = "__all__"
        read_only_fields = READ_ONLY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request.user, "tenant", None) if request and getattr(request.user, "is_authenticated", False) else None
        if tenant is not None:
            self.fields["class_teacher"].queryset = Teacher.objects.filter(
                tenant=tenant,
                is_deleted=False,
                staff__is_deleted=False,
                staff__status="active",
            )

    def get_class_teacher_name(self, obj) -> str | None:
        if obj.class_teacher and obj.class_teacher.staff:
            return obj.class_teacher.staff.full_name
        return None

    def get_student_count(self, obj) -> int:
        return obj.students.filter(status="active").count()

    def validate(self, attrs: dict) -> dict:
        if attrs.get("class_teacher") == "":
            attrs["class_teacher"] = None
        name = attrs.get("name") or getattr(self.instance, "name", None)
        code = attrs.get("code") or getattr(self.instance, "code", None)
        academic_year = attrs.get("academic_year") or getattr(self.instance, "academic_year", None)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Class name is required."})
        if not code or not str(code).strip():
            raise serializers.ValidationError({"code": "Class code is required."})
        if academic_year is None and self.instance is None:
            raise serializers.ValidationError({"academic_year": "Academic year is required."})
        return attrs


class ClassPrefectSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    stream_name = serializers.CharField(source="stream.name", read_only=True, allow_null=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = ClassPrefect
        fields = [
            "id", "student", "student_name", "admission_number",
            "school_class", "stream", "stream_name", "role", "role_display",
            "appointed_by", "tenant", "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY + ["appointed_by"]

    def validate(self, attrs: dict) -> dict:
        if attrs.get("stream") == "":
            attrs["stream"] = None

        student = attrs.get("student") or getattr(self.instance, "student", None)
        school_class = attrs.get("school_class") or getattr(self.instance, "school_class", None)
        stream = attrs.get("stream") if "stream" in attrs else getattr(self.instance, "stream", None)

        request = self.context.get("request")
        tenant = getattr(request.user, "tenant", None) if request else getattr(student, "tenant", None)

        if student and school_class and student.school_class_id != school_class.id:
            raise serializers.ValidationError({
                "student": "Student must belong to the selected class.",
            })
        if stream and school_class and stream.school_class_id != school_class.id:
            raise serializers.ValidationError({
                "stream": "Stream must belong to the selected class.",
            })
        if student and stream and student.stream_id and student.stream_id != stream.id:
            raise serializers.ValidationError({
                "student": "Student must belong to the selected stream.",
            })

        if tenant and student and school_class:
            duplicate = ClassPrefect.objects.filter(
                tenant=tenant,
                school_class=school_class,
                student=student,
                stream=stream,
                is_deleted=False,
            )
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError({
                    "student": "This student is already appointed as a class prefect for this scope.",
                })
        return attrs


class StreamSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    school_class_code = serializers.CharField(source="school_class.code", read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_student_count(self, obj) -> int:
        return obj.students.filter(status="active").count()

    def validate(self, attrs: dict) -> dict:
        name = attrs.get("name") or getattr(self.instance, "name", None)
        school_class = attrs.get("school_class") or getattr(self.instance, "school_class", None)
        if not name or not str(name).strip():
            raise serializers.ValidationError({"name": "Stream name is required."})
        if school_class is None and self.instance is None:
            raise serializers.ValidationError({"school_class": "Class is required."})
        return attrs


class SubjectPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectPaper
        fields = ["id", "subject", "code", "name", "sort_order", "created_at", "updated_at"]
        read_only_fields = READ_ONLY


class SubjectSerializer(serializers.ModelSerializer):
    papers = SubjectPaperSerializer(many=True, read_only=True)
    paper_codes = serializers.CharField(required=False, allow_blank=True, write_only=True)
    paper_codes_display = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id", "name", "code", "department", "description", "is_compulsory",
            "papers", "paper_codes", "paper_codes_display",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY

    def get_paper_codes_display(self, obj) -> str:
        return ", ".join(p.code for p in obj.papers.all())

    def _sync_paper_codes(self, subject: Subject, raw: str | None) -> None:
        if raw is None:
            return
        SubjectPaper.objects.filter(subject=subject).delete()
        codes = [part.strip() for part in raw.split(",") if part.strip()]
        for index, code in enumerate(codes, start=1):
            SubjectPaper.objects.create(
                tenant=subject.tenant,
                subject=subject,
                code=code,
                sort_order=index,
            )

    def create(self, validated_data):
        paper_codes = validated_data.pop("paper_codes", "")
        subject = super().create(validated_data)
        self._sync_paper_codes(subject, paper_codes)
        return subject

    def update(self, instance, validated_data):
        paper_codes = validated_data.pop("paper_codes", None)
        subject = super().update(instance, validated_data)
        if paper_codes is not None:
            self._sync_paper_codes(subject, paper_codes)
        return subject


class TimetableSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    subject_name = serializers.SerializerMethodField()
    subject_code = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    period_name = serializers.CharField(source="period.name", read_only=True)
    stream_name = serializers.CharField(source="stream.name", read_only=True)
    day_label = serializers.SerializerMethodField()
    is_schedule_locked = serializers.SerializerMethodField()

    class Meta:
        model = Timetable
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_subject_name(self, obj) -> str:
        if obj.subject_id:
            return obj.subject.name
        return obj.slot_label or ("Break" if obj.is_break_slot else "")

    def get_subject_code(self, obj) -> str:
        return obj.subject.code if obj.subject_id else ""

    def get_teacher_name(self, obj) -> str:
        if not obj.teacher_id:
            return ""
        staff = getattr(obj.teacher, "staff", None)
        return staff.full_name if staff else ""

    def get_day_label(self, obj) -> str:
        labels = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday",
        }
        return labels.get(obj.day_of_week, "") if obj.day_of_week is not None else ""

    def get_is_schedule_locked(self, obj) -> bool:
        if not obj.schedule_id:
            return False
        return bool(obj.schedule.is_locked or obj.schedule.status == "active")


class TimetableScheduleSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source="term.name", read_only=True)
    examination_session_name = serializers.CharField(
        source="examination_session.name", read_only=True,
    )

    class Meta:
        model = TimetableSchedule
        fields = "__all__"
        read_only_fields = READ_ONLY


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.staff.full_name", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    school_class_code = serializers.CharField(source="school_class.code", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "id", "tenant", "teacher", "teacher_name",
            "school_class", "school_class_name", "school_class_code",
            "subject", "subject_name", "subject_code",
            "academic_year", "academic_year_name",
            "is_active", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY + ["academic_year"]

    def validate(self, attrs: dict) -> dict:
        school_class = attrs.get("school_class") or getattr(self.instance, "school_class", None)
        teacher = attrs.get("teacher") or getattr(self.instance, "teacher", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        if school_class is None or teacher is None or subject is None:
            return attrs
        if school_class.tenant_id != teacher.tenant_id or school_class.tenant_id != subject.tenant_id:
            raise serializers.ValidationError("Teacher, class, and subject must belong to the same school.")
        attrs["academic_year"] = school_class.academic_year
        return attrs


class TeachingAssignmentBulkSerializer(serializers.Serializer):
    teacher = serializers.UUIDField()
    school_class = serializers.UUIDField()
    subject_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        min_length=1,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TeachingAssignmentEntrySerializer(serializers.Serializer):
    school_class = serializers.UUIDField()
    subject = serializers.UUIDField()


class TeachingAssignmentTeacherSyncSerializer(serializers.Serializer):
    teacher = serializers.UUIDField()
    assignments = serializers.ListField(
        child=TeachingAssignmentEntrySerializer(),
        allow_empty=False,
        min_length=1,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_assignments(self, value: list[dict]) -> list[dict]:
        seen: set[tuple[str, str]] = set()
        for entry in value:
            key = (str(entry["school_class"]), str(entry["subject"]))
            if key in seen:
                raise serializers.ValidationError(
                    "Each class and subject combination can only appear once per teacher.",
                )
            seen.add(key)
        return value


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = READ_ONLY


class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = "__all__"
        read_only_fields = READ_ONLY


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    homework_title = serializers.CharField(source="homework.title", read_only=True)

    class Meta:
        model = HomeworkSubmission
        fields = "__all__"
        read_only_fields = READ_ONLY


class AssessmentSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentScheme
        fields = "__all__"
        read_only_fields = READ_ONLY

    def create(self, validated_data):
        if validated_data.get("is_default"):
            tenant = self.context["request"].user.tenant
            AssessmentScheme.objects.filter(tenant=tenant, is_default=True, is_deleted=False).update(is_default=False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default"):
            AssessmentScheme.objects.filter(
                tenant=instance.tenant, is_default=True, is_deleted=False,
            ).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


class SubjectCombinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectCombination
        fields = "__all__"
        read_only_fields = READ_ONLY


class StudentSubjectRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = StudentSubjectRegistration
        fields = "__all__"
        read_only_fields = READ_ONLY


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = "__all__"
        read_only_fields = READ_ONLY


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = "__all__"
        read_only_fields = READ_ONLY


class ClassNoticeSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ClassNotice
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_author_name(self, obj) -> str | None:
        if obj.author and obj.author.staff:
            return obj.author.staff.full_name
        return None


class DisciplineRemarkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DisciplineRemark
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_recorded_by_name(self, obj) -> str | None:
        if obj.recorded_by and obj.recorded_by.staff:
            return obj.recorded_by.staff.full_name
        return None