from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import ItemViewSet, StockMovementViewSet, ProcurementViewSet

router = DefaultRouter()
router.register("items", ItemViewSet, basename="item")
router.register("movements", StockMovementViewSet, basename="stock-movement")
router.register("procurements", ProcurementViewSet, basename="procurement")

urlpatterns = [path("", include(router.urls))]
