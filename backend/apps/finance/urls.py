from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.finance.billing_views import (
    BillClassView,
    BillStudentView,
    GatewayWebhookView,
    InvoicePdfView,
    OnlinePaymentInitiateView,
    PaymentReceiptPdfView,
    StudentStatementPdfView,
)
from apps.finance.results_access_views import ClassResultsAccessPolicyView, ResultsAccessPolicyView
from apps.finance.views import (
    AccountingEntryViewSet,
    AccountingPeriodViewSet,
    BudgetViewSet,
    FeeCategoryViewSet,
    FeeDiscountViewSet,
    FeePaymentViewSet,
    FeeStructureViewSet,
    FinanceAnalyticsView,
    FinanceNoteViewSet,
    FinanceReportsView,
    FinanceWorkspaceView,
    FinancialAccountViewSet,
    InvoiceViewSet,
    MiscIncomeViewSet,
    ParentFeeStatementsView,
    RefundViewSet,
    StudentFeeBalanceViewSet,
    TransactionApprovalQueueView,
)

router = DefaultRouter()
router.register("fee-categories", FeeCategoryViewSet, basename="fee-category")
router.register("fee-structures", FeeStructureViewSet, basename="fee-structure")
router.register("balances", StudentFeeBalanceViewSet, basename="student-fee-balance")
router.register("payments", FeePaymentViewSet, basename="fee-payment")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("discounts", FeeDiscountViewSet, basename="fee-discount")
router.register("refunds", RefundViewSet, basename="refund")
router.register("misc-income", MiscIncomeViewSet, basename="misc-income")
router.register("notes", FinanceNoteViewSet, basename="finance-note")
router.register("accounts", FinancialAccountViewSet, basename="financial-account")
router.register("budgets", BudgetViewSet, basename="budget")
router.register("periods", AccountingPeriodViewSet, basename="accounting-period")
router.register("accounting", AccountingEntryViewSet, basename="accounting-entry")

urlpatterns = [
    path("workspace/", FinanceWorkspaceView.as_view(), name="finance-workspace"),
    path("approval-queue/", TransactionApprovalQueueView.as_view(), name="finance-approval-queue"),
    path("analytics/", FinanceAnalyticsView.as_view(), name="finance-analytics"),
    path("reports/", FinanceReportsView.as_view(), name="finance-reports"),
    path("parent-statements/", ParentFeeStatementsView.as_view(), name="finance-parent-statements"),
    path("results-access-policy/", ResultsAccessPolicyView.as_view(), name="finance-results-access-policy"),
    path(
        "results-access-policy/classes/<uuid:class_id>/",
        ClassResultsAccessPolicyView.as_view(),
        name="finance-class-results-access-policy",
    ),
    # Billing engine
    path("billing/bill-class/", BillClassView.as_view(), name="finance-bill-class"),
    path("billing/bill-student/", BillStudentView.as_view(), name="finance-bill-student"),
    # Documents
    path("payments/<uuid:pk>/receipt.pdf", PaymentReceiptPdfView.as_view(), name="finance-payment-receipt-pdf"),
    path("invoices/<uuid:pk>/pdf/", InvoicePdfView.as_view(), name="finance-invoice-pdf"),
    path(
        "statements/<uuid:student_id>/pdf/",
        StudentStatementPdfView.as_view(),
        name="finance-student-statement-pdf",
    ),
    # Gateway architecture (no live providers)
    path("online-payments/", OnlinePaymentInitiateView.as_view(), name="finance-online-payments"),
    path(
        "gateways/<str:gateway_slug>/webhook/",
        GatewayWebhookView.as_view(),
        name="finance-gateway-webhook",
    ),
    path("", include(router.urls)),
]
