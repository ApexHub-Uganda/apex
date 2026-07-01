from apps.core.constants import UserRole
from apps.core.permissions import HasRole, IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.finance.models import AccountingEntry, FeePayment, FeeStructure, Invoice
from apps.finance.serializers import AccountingEntrySerializer, FeePaymentSerializer, FeeStructureSerializer, InvoiceSerializer

class FeeStructureViewSet(BaseModelViewSet):
    required_feature_key = "fee_structures"
    queryset = FeeStructure.objects.select_related("school_class", "term")
    serializer_class = FeeStructureSerializer
    permission_classes = [HasRole([UserRole.FINANCE_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["school_class", "term"]

class FeePaymentViewSet(BaseModelViewSet):
    required_feature_key = "payment_recording"
    queryset = FeePayment.objects.select_related("student", "fee_structure", "received_by")
    serializer_class = FeePaymentSerializer
    permission_classes = [HasRole([UserRole.FINANCE_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["student", "status", "payment_method"]

class InvoiceViewSet(BaseModelViewSet):
    required_feature_key = "invoice_generation"
    queryset = Invoice.objects.select_related("student")
    serializer_class = InvoiceSerializer
    permission_classes = [HasRole([UserRole.FINANCE_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["student", "status"]
    search_fields = ["invoice_number"]

class AccountingEntryViewSet(BaseModelViewSet):
    required_feature_key = "expenses"
    queryset = AccountingEntry.objects.select_related("fee_payment")
    serializer_class = AccountingEntrySerializer
    permission_classes = [HasRole([UserRole.FINANCE_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["entry_date"]
