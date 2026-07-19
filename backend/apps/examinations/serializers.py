from __future__ import annotations

from rest_framework import serializers

from apps.examinations.models import (
    ReportCardSubjectLine,
    Exam,
    ExaminationSession,
    Grade,
    GradingScale,
    GradingScheme,
    GradingSchemeBand,
    ReportCard,
)

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class GradingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingScale
        fields = "__all__"
        read_only_fields = READ_ONLY


class GradingSchemeBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingSchemeBand
        fields = [
            "id", "scheme", "min_score", "max_score", "grade",
            "grade_point", "remarks", "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY


class GradingSchemeSerializer(serializers.ModelSerializer):
    bands = serializers.SerializerMethodField()
    band_count = serializers.SerializerMethodField()

    class Meta:
        model = GradingScheme
        fields = [
            "id", "name", "description", "is_default", "bands", "band_count",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY

    def get_bands(self, obj: GradingScheme) -> list:
        active = obj.bands.filter(is_deleted=False).order_by("-min_score")
        return GradingSchemeBandSerializer(active, many=True).data

    def get_band_count(self, obj: GradingScheme) -> int:
        return obj.bands.filter(is_deleted=False).count()


class GradingSchemeBandInputSerializer(serializers.Serializer):
    min_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    grade = serializers.CharField(max_length=5)
    grade_point = serializers.DecimalField(max_digits=3, decimal_places=1, required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class GradingSchemeSyncSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    is_default = serializers.BooleanField(required=False, default=False)
    bands = serializers.ListField(
        child=GradingSchemeBandInputSerializer(),
        allow_empty=False,
        min_length=1,
    )


class GradeCalculationApplySerializer(serializers.Serializer):
    scheme = serializers.UUIDField()
    exam = serializers.UUIDField()


WORKFLOW_READ_ONLY = [
    "lifecycle_status", "published_at", "published_by",
    "marks_status", "marks_submitted_at", "marks_submitted_by",
    "marks_approved_at", "marks_approved_by",
    "marks_locked_at", "marks_locked_by",
    "marks_reopened_at", "marks_reopened_by", "marks_reopen_reason",
]


class ExaminationSessionSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = ExaminationSession
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs: dict) -> dict:
        if self.instance is None:
            from apps.academics.singleton import assert_can_create_examination_session

            request = self.context.get("request")
            tenant = getattr(request.user, "tenant", None) if request else None
            if tenant is not None:
                assert_can_create_examination_session(tenant)
        return attrs


class ExamSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    paper_code = serializers.CharField(source="paper.code", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.SerializerMethodField()
    examination_session_name = serializers.CharField(source="examination_session.name", read_only=True)

    def get_term_name(self, obj) -> str:
        return obj.term.name if obj.term_id else ""

    class Meta:
        model = Exam
        fields = [
            "id", "name", "subject", "subject_name", "paper", "paper_code",
            "school_class", "school_class_name", "term", "term_name",
            "examination_session", "examination_session_name",
            "exam_date", "max_score", "weight", "exam_type",
            "lifecycle_status", "published_at", "published_by",
            "marks_status", "marks_submitted_at", "marks_submitted_by",
            "marks_approved_at", "marks_approved_by",
            "marks_locked_at", "marks_locked_by",
            "marks_reopened_at", "marks_reopened_by", "marks_reopen_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY + WORKFLOW_READ_ONLY

    def validate(self, attrs):
        paper = attrs.get("paper", getattr(self.instance, "paper", None))
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        if paper and subject and paper.subject_id != subject.id:
            raise serializers.ValidationError({"paper": "Paper must belong to the selected subject."})
        return attrs


class GradeSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    subject_name = serializers.CharField(source="exam.subject.name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    max_score = serializers.DecimalField(source="exam.max_score", max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = Grade
        fields = [
            "id", "exam", "exam_name", "subject_name", "student", "student_name",
            "student_admission_number", "score", "grade", "remarks", "entry_status",
            "max_score", "graded_by", "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY + ["grade", "entry_status"]


class ReportCardSubjectLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCardSubjectLine
        fields = (
            "id", "subject", "subject_name", "subject_code", "paper_breakdown",
            "ca_score", "exam_score", "total_score", "max_score", "grade",
            "grade_point", "remarks", "sort_order",
        )
        read_only_fields = fields


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    stream_name = serializers.CharField(source="stream.name", read_only=True, allow_null=True)
    subject_lines = ReportCardSubjectLineSerializer(many=True, read_only=True)

    class Meta:
        model = ReportCard
        fields = (
            "id", "student", "student_name", "admission_number", "term", "term_name",
            "school_class", "class_name", "stream", "stream_name", "academic_year",
            "version", "is_latest", "total_score", "average_score", "rank", "stream_rank",
            "class_size", "stream_size", "aggregate_points", "division",
            "remarks", "teacher_remarks", "principal_remarks", "dos_remarks",
            "is_published", "published_at", "days_present", "days_absent", "days_late",
            "days_excused", "next_term_opens", "subject_lines", "created_at", "updated_at",
        )
        read_only_fields = [f for f in fields if f not in ("teacher_remarks", "principal_remarks", "dos_remarks", "remarks")]


class MarksEntryBulkSerializer(serializers.Serializer):
    exam = serializers.UUIDField()
    entries = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )


class ExamWorkflowActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")