from __future__ import annotations

from rest_framework import serializers

from apps.examinations.models import Exam, Grade, GradingScale, ReportCard

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class GradingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingScale
        fields = "__all__"
        read_only_fields = READ_ONLY


class ExamSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    paper_code = serializers.CharField(source="paper.code", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id", "name", "subject", "subject_name", "paper", "paper_code",
            "school_class", "school_class_name", "term", "term_name",
            "exam_date", "max_score", "weight", "exam_type",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY

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
            "student_admission_number", "score", "grade", "remarks", "max_score",
            "graded_by", "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY + ["grade"]


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)

    class Meta:
        model = ReportCard
        fields = [
            "id", "student", "student_name", "term", "term_name",
            "school_class", "school_class_name", "total_score", "average_score",
            "rank", "remarks", "teacher_remarks", "principal_remarks", "is_published",
            "created_at", "updated_at",
        ]
        read_only_fields = READ_ONLY


class MarksEntryBulkSerializer(serializers.Serializer):
    exam = serializers.UUIDField()
    entries = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )