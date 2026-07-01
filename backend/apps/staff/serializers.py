from rest_framework import serializers
from apps.staff.models import Staff, Teacher
class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class TeacherSerializer(serializers.ModelSerializer):
    staff_detail = StaffSerializer(source="staff", read_only=True)
    class Meta:
        model = Teacher
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
