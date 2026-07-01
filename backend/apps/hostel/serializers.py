from rest_framework import serializers
from apps.hostel.models import Allocation, Hostel, Room
class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
