from rest_framework import serializers

from apps.attendance.models import AttendanceRecord, LessonAttendanceEntry, LessonAttendanceSession

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"
        read_only_fields = READ_ONLY


class LessonAttendanceSessionSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.SerializerMethodField()
    entry_count = serializers.SerializerMethodField()

    class Meta:
        model = LessonAttendanceSession
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_teacher_name(self, obj) -> str | None:
        if obj.teacher and obj.teacher.staff:
            return obj.teacher.staff.full_name
        return None

    def get_entry_count(self, obj) -> int:
        return obj.entries.filter(is_deleted=False).count()


class LessonAttendanceEntrySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)

    class Meta:
        model = LessonAttendanceEntry
        fields = "__all__"
        read_only_fields = READ_ONLY