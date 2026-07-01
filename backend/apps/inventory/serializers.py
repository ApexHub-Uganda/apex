from rest_framework import serializers
from apps.inventory.models import Item, Procurement, StockMovement
class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class ProcurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procurement
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
