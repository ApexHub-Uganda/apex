from rest_framework import serializers

from apps.academics.models import AcademicYear, Assignment, Class, Department, Homework, Stream, Subject, Term, Timetable

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = READ_ONLY


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = READ_ONLY


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = READ_ONLY


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = "__all__"
        read_only_fields = READ_ONLY


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = "__all__"
        read_only_fields = READ_ONLY


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = READ_ONLY


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