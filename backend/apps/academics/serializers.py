from rest_framework import serializers

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

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = READ_ONLY


class TermSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)

    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = READ_ONLY


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

    class Meta:
        model = Class
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_class_teacher_name(self, obj) -> str | None:
        if obj.class_teacher and obj.class_teacher.staff:
            return obj.class_teacher.staff.full_name
        return None

    def get_student_count(self, obj) -> int:
        return obj.students.filter(status="active").count()


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = "__all__"
        read_only_fields = READ_ONLY


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
    class Meta:
        model = Timetable
        fields = "__all__"
        read_only_fields = READ_ONLY


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