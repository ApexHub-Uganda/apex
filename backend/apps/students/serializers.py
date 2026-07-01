from rest_framework import serializers

from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]

    def get_full_name(self, obj: Student) -> str:
        return f"{obj.first_name} {obj.last_name}"


class AdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]