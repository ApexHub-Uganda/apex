from django.urls import include, path
from rest_framework.routers import DefaultRouter

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
    path("", include(router.urls)),
]