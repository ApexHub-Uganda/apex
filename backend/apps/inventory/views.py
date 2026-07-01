from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.inventory.models import Item, Procurement, StockMovement
from apps.inventory.serializers import ItemSerializer, ProcurementSerializer, StockMovementSerializer

class ItemViewSet(BaseModelViewSet):
    required_feature_key = "inventory_items"
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "sku"]
    filterset_fields = ["category"]

class StockMovementViewSet(BaseModelViewSet):
    required_feature_key = "stock_movement"
    queryset = StockMovement.objects.select_related("item", "performed_by")
    serializer_class = StockMovementSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["item", "movement_type"]

class ProcurementViewSet(BaseModelViewSet):
    required_feature_key = "purchase_orders"
    queryset = Procurement.objects.select_related("approved_by")
    serializer_class = ProcurementSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]
