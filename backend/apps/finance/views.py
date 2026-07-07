from __future__ import annotations

import csv
import io
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import UserRole
from apps.core.permissions import IsSchoolPortalUser, IsStaffMember, RequiresAnyFeature, RequiresFeature, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.finance.constants import APPROVAL_APPROVED, APPROVAL_PENDING
from apps.finance.mixins import FinanceScopeMixin
from apps.finance.models import (
    AccountingEntry,
    AccountingPeriod,
    Budget,
    FeeCategory,
    FeeDiscount,
    FeePayment,
    FeeStructure,
    FinanceNote,
    FinancialAccount,
    Invoice,
    MiscIncome,
    Refund,
    StudentFeeBalance,
)
from apps.finance.serializers import (
    AccountingEntrySerializer,
    AccountingPeriodSerializer,
    BudgetSerializer,
    FeeCategorySerializer,
    FeeDiscountSerializer,
    FeePaymentSerializer,
    FeeStructureSerializer,
    FinanceNoteSerializer,
    FinancialAccountSerializer,
    InvoiceSerializer,
    MiscIncomeSerializer,
    RefundSerializer,
    StudentFeeBalanceSerializer,
)
from apps.finance.reports import build_finance_analytics, build_finance_reports, build_parent_fee_statement
from apps.finance.workflow import (
    FinanceWorkflowError,
    approve_discount,
    approve_payment,
    approve_refund,
    assistant_bursar_requires_approval,
    close_accounting_period,
    generate_receipt_number,
    reopen_accounting_period,
    reverse_payment,
)
from apps.finance.workspaces import build_finance_workspace
from apps.students.models import Parent, Student


class FeeCategoryViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "fee_categories"
    queryset = FeeCategory.objects.all()
    serializer_class = FeeCategorySerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["name", "code"]


class FeeStructureViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "fee_structures"
    queryset = FeeStructure.objects.select_related("school_class", "term", "category")
    serializer_class = FeeStructureSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["school_class", "term", "fee_category", "category"]


class StudentFeeBalanceViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "debtor_management"
    queryset = StudentFeeBalance.objects.select_related("student", "student__school_class", "term")
    serializer_class = StudentFeeBalanceSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "term", "status"]
    http_method_names = ["get", "head", "options"]


class FeePaymentViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "payment_recording"
    queryset = FeePayment.objects.select_related("student", "fee_structure", "received_by", "approved_by")
    serializer_class = FeePaymentSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "status", "payment_method", "approval_status"]

    _WORKFLOW_FEATURES = {
        "approve": "transaction_approval",
        "reverse": "transaction_approval",
        "receipt": "payment_recording",
    }

    def get_permissions(self):
        perms = [permission() for permission in self.permission_classes]
        feature_key = self._WORKFLOW_FEATURES.get(
            getattr(self, "action", None),
            self.required_feature_key,
        )
        if feature_key:
            perms.append(RequiresFeature(feature_key)())
        return perms

    def perform_create(self, serializer):
        user = self.request.user
        approval_status = APPROVAL_PENDING if assistant_bursar_requires_approval(user) else APPROVAL_APPROVED
        status_val = "pending" if approval_status == APPROVAL_PENDING else "completed"
        receipt_number = ""
        if approval_status == APPROVAL_APPROVED:
            receipt_number = generate_receipt_number(tenant=user.tenant)
        serializer.save(
            tenant=user.tenant,
            received_by=user,
            approval_status=approval_status,
            status=status_val,
            receipt_number=receipt_number,
            created_by=user,
            updated_by=user,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        payment = self.get_object()
        try:
            approve_payment(payment=payment, user=request.user)
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment.refresh_from_db()
        return Response({
            "success": True,
            "message": "Payment approved.",
            "data": FeePaymentSerializer(payment).data,
        })

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        payment = self.get_object()
        try:
            reverse_payment(
                payment=payment,
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment.refresh_from_db()
        return Response({
            "success": True,
            "message": "Payment reversed.",
            "data": FeePaymentSerializer(payment).data,
        })

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        tenant = request.user.tenant
        school_name = tenant.name if tenant else "School"
        return Response({
            "success": True,
            "data": {
                "receipt_number": payment.receipt_number,
                "school_name": school_name,
                "student_name": payment.student.full_name if payment.student_id else "",
                "admission_number": payment.student.admission_number if payment.student_id else "",
                "class_name": payment.student.school_class.name if payment.student_id and payment.student.school_class_id else "",
                "fee_item": payment.fee_structure.name if payment.fee_structure_id else "",
                "amount_paid": str(payment.amount_paid),
                "payment_date": str(payment.payment_date),
                "payment_method": payment.payment_method,
                "reference": payment.reference,
                "mpesa_transaction_id": payment.mpesa_transaction_id,
                "received_by": payment.received_by.full_name if payment.received_by_id else "",
                "approved_by": payment.approved_by.full_name if payment.approved_by_id else "",
                "status": payment.status,
                "approval_status": payment.approval_status,
            },
        })


class InvoiceViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "invoice_generation"
    queryset = Invoice.objects.select_related("student")
    serializer_class = InvoiceSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "status"]
    search_fields = ["invoice_number"]


class FeeDiscountViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "discounts"
    queryset = FeeDiscount.objects.select_related("student", "fee_structure", "invoice", "approved_by")
    serializer_class = FeeDiscountSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "status", "discount_type"]

    def get_permissions(self):
        perms = super().get_permissions()
        if getattr(self, "action", None) == "approve":
            perms.append(RequiresFeature("transaction_approval")())
        return perms

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        discount = self.get_object()
        try:
            approve_discount(discount=discount, user=request.user)
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        discount.refresh_from_db()
        return Response({
            "success": True,
            "message": "Discount approved.",
            "data": FeeDiscountSerializer(discount).data,
        })


class RefundViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "refunds"
    queryset = Refund.objects.select_related("fee_payment", "fee_payment__student", "approved_by")
    serializer_class = RefundSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "fee_payment"]

    def get_permissions(self):
        perms = super().get_permissions()
        if getattr(self, "action", None) == "approve":
            perms.append(RequiresFeature("transaction_approval")())
        return perms

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        refund = self.get_object()
        try:
            approve_refund(refund=refund, user=request.user)
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        refund.refresh_from_db()
        return Response({
            "success": True,
            "message": "Refund processed.",
            "data": RefundSerializer(refund).data,
        })


class MiscIncomeViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "misc_income"
    queryset = MiscIncome.objects.select_related("account", "recorded_by")
    serializer_class = MiscIncomeSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["income_date", "account"]

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            recorded_by=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class FinanceNoteViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "finance_notes"
    queryset = FinanceNote.objects.select_related("student", "invoice", "fee_payment", "author")
    serializer_class = FinanceNoteSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["student", "invoice", "fee_payment"]

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            author=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class FinancialAccountViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "financial_accounts"
    queryset = FinancialAccount.objects.all()
    serializer_class = FinancialAccountSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["account_type", "is_active"]


class BudgetViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "budget_management"
    queryset = Budget.objects.select_related("academic_year", "term", "account")
    serializer_class = BudgetSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["academic_year", "term"]


class AccountingPeriodViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "accounting_periods"
    queryset = AccountingPeriod.objects.select_related("closed_by")
    serializer_class = AccountingPeriodSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status"]

    def get_permissions(self):
        perms = super().get_permissions()
        if getattr(self, "action", None) in {"close_period", "reopen_period"}:
            perms.append(RequiresFeature("transaction_approval")())
        return perms

    @action(detail=True, methods=["post"], url_path="close")
    def close_period(self, request, pk=None):
        period = self.get_object()
        try:
            close_accounting_period(period=period, user=request.user)
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        period.refresh_from_db()
        return Response({
            "success": True,
            "message": "Accounting period closed.",
            "data": AccountingPeriodSerializer(period).data,
        })

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen_period(self, request, pk=None):
        period = self.get_object()
        try:
            reopen_accounting_period(period=period, user=request.user)
        except FinanceWorkflowError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        period.refresh_from_db()
        return Response({
            "success": True,
            "message": "Accounting period reopened.",
            "data": AccountingPeriodSerializer(period).data,
        })


class AccountingEntryViewSet(FinanceScopeMixin, BaseModelViewSet):
    required_feature_key = "expenses"
    queryset = AccountingEntry.objects.select_related("fee_payment", "account", "approved_by")
    serializer_class = AccountingEntrySerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["entry_date", "entry_type", "approval_status"]


class TransactionApprovalQueueView(APIView):
    """Pending payments, discounts, and refunds for bursar review."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("transaction_approval")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"payments": [], "discounts": [], "refunds": []}})

        payments = FeePayment.objects.filter(
            tenant=tenant, is_deleted=False, approval_status=APPROVAL_PENDING,
        ).select_related("student", "fee_structure")[:50]
        discounts = FeeDiscount.objects.filter(
            tenant=tenant, is_deleted=False, status="pending",
        ).select_related("student")[:50]
        refunds = Refund.objects.filter(
            tenant=tenant, is_deleted=False, status="pending",
        ).select_related("fee_payment", "fee_payment__student")[:50]

        return Response({
            "success": True,
            "data": {
                "payments": FeePaymentSerializer(payments, many=True).data,
                "discounts": FeeDiscountSerializer(discounts, many=True).data,
                "refunds": RefundSerializer(refunds, many=True).data,
                "count": payments.count() + discounts.count() + refunds.count(),
            },
        })


class FinanceWorkspaceView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresAnyFeature("bursar_workspace", "assistant_bursar_workspace")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        return Response({
            "success": True,
            "data": build_finance_workspace(tenant=tenant, user=request.user),
        })


class FinanceAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("finance_analytics")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {}})
        return Response({
            "success": True,
            "data": build_finance_analytics(tenant=tenant),
        })


class FinanceReportsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("financial_reports")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"rows": [], "totals": {}}})

        report_type = request.query_params.get("type", "collections")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        export_format = request.query_params.get("format", "json")

        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        data = build_finance_reports(
            tenant=tenant,
            report_type=report_type,
            start_date=parsed_start,
            end_date=parsed_end,
        )

        if export_format == "csv":
            rows = data.get("rows") or []
            if not rows:
                return HttpResponse("No data", content_type="text/plain", status=404)
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            response = HttpResponse(buffer.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="finance-{report_type}.csv"'
            return response

        return Response({"success": True, "data": data})


class ParentFeeStatementsView(APIView):
    """Read-only fee statements scoped to a parent's linked children."""

    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("parent_fee_statements")())
        return perms

    def get(self, request):
        user = request.user
        tenant = user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"children": []}})

        student_id = request.query_params.get("student_id")
        parent = getattr(user, "parent_profile", None)

        from apps.finance.scoping import user_has_school_wide_finance_access

        if user.role == UserRole.PARENT:
            if parent is None:
                return Response({"success": True, "data": {"children": []}})
            children = parent.children.filter(tenant=tenant, is_deleted=False)
            if student_id:
                children = children.filter(pk=student_id)
        elif user_has_school_wide_finance_access(user, tenant) or user.role in (
            UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN,
        ):
            if request.query_params.get("parent_id"):
                parent = Parent.objects.filter(tenant=tenant, pk=request.query_params["parent_id"]).first()
                if parent:
                    children = parent.children.filter(tenant=tenant, is_deleted=False)
                else:
                    children = Student.objects.none()
            else:
                children = Student.objects.filter(tenant=tenant, is_deleted=False)
            if student_id:
                children = children.filter(pk=student_id)
        else:
            return Response(
                {"success": False, "message": "Fee statements are only available to parents or authorized staff."},
                status=status.HTTP_403_FORBIDDEN,
            )

        statements = [build_parent_fee_statement(tenant=tenant, student=child) for child in children]
        return Response({
            "success": True,
            "data": {
                "children": statements,
                "count": len(statements),
            },
        })