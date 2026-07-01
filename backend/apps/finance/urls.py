from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.finance.views import FeeStructureViewSet, FeePaymentViewSet, InvoiceViewSet, AccountingEntryViewSet

router = DefaultRouter()
router.register("fee-structures", FeeStructureViewSet, basename="fee-structure")
router.register("payments", FeePaymentViewSet, basename="fee-payment")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("accounting", AccountingEntryViewSet, basename="accounting-entry")

urlpatterns = [path("", include(router.urls))]
