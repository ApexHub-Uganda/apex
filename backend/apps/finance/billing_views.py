"""Billing, document PDF, and online payment gateway endpoints."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Class, Term
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsSchoolPortalUser, IsStaffMember, RequiresFeature, TenantActivePermission
from apps.finance.models import FeePayment, Invoice
from apps.finance.reports import build_parent_fee_statement
from apps.finance.services.billing import BillingError, bill_class_for_term, bill_student_for_term
from apps.finance.services.documents import (
    build_invoice_pdf,
    build_receipt_pdf,
    build_student_statement_pdf,
)
from apps.finance.services.gateway import list_gateways
from apps.finance.services.gateway.service import handle_gateway_webhook, initiate_online_payment
from apps.students.models import Student
from apps.tenants.role_permissions import user_can_access_feature


class BillClassView(APIView):
    """Bulk-bill all active students in a class for a term from fee structures."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresFeature("student_billing")(),
        ]

    def post(self, request: Request) -> Response:
        tenant = request.user.tenant
        class_id = request.data.get("school_class") or request.data.get("class_id")
        term_id = request.data.get("term") or request.data.get("term_id")
        if not class_id or not term_id:
            return Response(
                {"success": False, "message": "school_class and term are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        school_class = Class.objects.filter(tenant=tenant, pk=class_id, is_deleted=False).first()
        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
        if not school_class or not term:
            return Response(
                {"success": False, "message": "Class or term not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            result = bill_class_for_term(
                tenant=tenant,
                school_class=school_class,
                term=term,
                actor=request.user,
                only_mandatory=bool(request.data.get("only_mandatory", True)),
                student_ids=request.data.get("student_ids"),
                due_date=request.data.get("due_date") or None,
                request=request,
            )
        except BillingError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "data": result})


class BillStudentView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresFeature("student_billing")(),
        ]

    def post(self, request: Request) -> Response:
        tenant = request.user.tenant
        student = Student.objects.filter(
            tenant=tenant, pk=request.data.get("student"), is_deleted=False,
        ).first()
        term = Term.objects.filter(
            tenant=tenant, pk=request.data.get("term"), is_deleted=False,
        ).first()
        if not student or not term:
            return Response(
                {"success": False, "message": "Student or term not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            inv = bill_student_for_term(
                tenant=tenant,
                student=student,
                term=term,
                actor=request.user,
                only_mandatory=bool(request.data.get("only_mandatory", True)),
                skip_if_exists=bool(request.data.get("skip_if_exists", True)),
                request=request,
            )
        except BillingError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "success": True,
            "data": {
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "total_amount": str(inv.total_amount),
            },
        })


class PaymentReceiptPdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresFeature("payment_recording")(),
        ]

    def get(self, request: Request, pk=None):
        payment = FeePayment.objects.filter(
            tenant=request.user.tenant, pk=pk, is_deleted=False,
        ).select_related("student", "fee_structure", "received_by").first()
        if not payment:
            return Response({"success": False, "message": "Payment not found."}, status=404)
        pdf = build_receipt_pdf(tenant=request.user.tenant, payment=payment, request=request)
        name = payment.receipt_number or f"receipt-{pk}"
        return pdf_attachment_response(pdf_bytes=pdf, filename=f"{name}.pdf")


class InvoicePdfView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresFeature("invoice_generation")(),
        ]

    def get(self, request: Request, pk=None):
        inv = Invoice.objects.filter(
            tenant=request.user.tenant, pk=pk, is_deleted=False,
        ).select_related("student").first()
        if not inv:
            return Response({"success": False, "message": "Invoice not found."}, status=404)
        pdf = build_invoice_pdf(tenant=request.user.tenant, invoice=inv, request=request)
        return pdf_attachment_response(pdf_bytes=pdf, filename=f"{inv.invoice_number}.pdf")


class StudentStatementPdfView(APIView):
    """Staff or parent (own children) fee statement PDF."""

    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request: Request, student_id=None):
        tenant = request.user.tenant
        student = Student.objects.filter(tenant=tenant, pk=student_id, is_deleted=False).first()
        if not student:
            return Response({"success": False, "message": "Student not found."}, status=404)

        # Permission: feature flag + ownership for parents
        from apps.core.constants import UserRole, normalize_role
        role = normalize_role(getattr(request.user, "role", ""))
        if role == UserRole.PARENT:
            parent = getattr(request.user, "parent_profile", None)
            if parent is None or not parent.children.filter(pk=student.id).exists():
                return Response({"success": False, "message": "Not your child."}, status=403)
            if not user_can_access_feature(tenant, request.user, "parent_fee_statements", require_write=False):
                return Response({"success": False, "message": "Feature not enabled."}, status=403)
        else:
            if not (
                user_can_access_feature(tenant, request.user, "parent_fee_statements", require_write=False)
                or user_can_access_feature(tenant, request.user, "student_billing", require_write=False)
                or user_can_access_feature(tenant, request.user, "debtor_management", require_write=False)
            ):
                return Response({"success": False, "message": "Feature not enabled."}, status=403)

        statement = build_parent_fee_statement(tenant=tenant, student=student)
        pdf = build_student_statement_pdf(
            tenant=tenant, student=student, statement=statement, request=request,
        )
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"statement-{student.admission_number}.pdf",
        )


class OnlinePaymentInitiateView(APIView):
    """Gateway architecture endpoint — always returns not-configured until providers enabled."""

    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request: Request) -> Response:
        return Response({
            "success": True,
            "data": {
                "gateways": list_gateways(),
                "message": "Payment gateway not yet configured.",
            },
        })

    def post(self, request: Request) -> Response:
        tenant = request.user.tenant
        result = initiate_online_payment(
            tenant=tenant, user=request.user, payload=request.data, request=request,
        )
        return Response(
            {"success": False, "data": result, "message": result.get("message")},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class GatewayWebhookView(APIView):
    """Webhook receiver shell (no auth for future provider callbacks; validates via adapter)."""

    permission_classes = []  # signature validation inside adapter when live
    authentication_classes = []

    def post(self, request: Request, gateway_slug: str) -> Response:
        # Without tenant context from provider config, accept and store as unscoped log if possible
        tenant = None
        body = request.body or b""
        result = handle_gateway_webhook(
            tenant=tenant,
            gateway_slug=gateway_slug,
            headers=dict(request.headers),
            body=body,
            request=request,
        )
        return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)
