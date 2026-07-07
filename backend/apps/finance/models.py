"""Finance models."""
from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel
from apps.finance.constants import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    APPROVAL_REVERSED,
    BALANCE_CLEARED,
    BALANCE_DEBTOR,
    DISCOUNT_APPROVED,
    DISCOUNT_PENDING,
    DISCOUNT_REJECTED,
    PERIOD_CLOSED,
    PERIOD_OPEN,
    REFUND_PENDING,
    REFUND_PROCESSED,
    REFUND_REJECTED,
)


class FeeCategory(BaseModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Fee categories"


class FeeStructure(BaseModel):
    name = models.CharField(max_length=255)
    fee_category = models.CharField(
        max_length=30,
        choices=[
            ("tuition", "Tuition"),
            ("boarding", "Boarding"),
            ("transport", "Transport"),
            ("meals", "Meals"),
            ("activity", "Activity / Clubs"),
            ("exam", "Examination"),
            ("uniform", "Uniform"),
            ("development", "Development Levy"),
            ("other", "Other"),
        ],
        default="tuition",
    )
    category = models.ForeignKey(
        FeeCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="fee_structures",
    )
    vote_head_code = models.CharField(max_length=30, blank=True, help_text="Government vote head / account code")
    school_class = models.ForeignKey("academics.Class", on_delete=models.CASCADE, related_name="fee_structures")
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="fee_structures")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="UGX")
    frequency = models.CharField(
        max_length=20,
        choices=[
            ("once", "One-time"),
            ("termly", "Per Term"),
            ("annual", "Annual"),
            ("monthly", "Monthly"),
        ],
        default="termly",
    )
    due_date = models.DateField()
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["due_date"]


class StudentFeeBalance(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_balances")
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="fee_balances")
    total_billed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField(
        max_length=20,
        choices=[
            (BALANCE_DEBTOR, "Debtor"),
            (BALANCE_CLEARED, "Cleared"),
            ("credit", "Credit"),
        ],
        default=BALANCE_DEBTOR,
    )

    class Meta:
        unique_together = [("tenant", "student", "term")]
        ordering = ["-balance"]


class FeePayment(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_payments")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="payments")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash", "Cash"), ("bank", "Bank Transfer"), ("mpesa", "M-Pesa"),
            ("card", "Card"), ("cheque", "Cheque"),
        ],
        default="cash",
    )
    reference = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=50, blank=True, db_index=True)
    mpesa_transaction_id = models.CharField(max_length=50, blank=True)
    mpesa_phone = models.CharField(max_length=20, blank=True)
    received_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="received_payments")
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"), ("completed", "Completed"),
            ("failed", "Failed"), ("refunded", "Refunded"),
        ],
        default="completed",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=[
            (APPROVAL_PENDING, "Pending Approval"),
            (APPROVAL_APPROVED, "Approved"),
            (APPROVAL_REJECTED, "Rejected"),
            (APPROVAL_REVERSED, "Reversed"),
        ],
        default=APPROVAL_APPROVED,
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_payments",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date"]
        indexes = [models.Index(fields=["tenant", "status", "payment_date"])]


class Invoice(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50, db_index=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"), ("sent", "Sent"), ("paid", "Paid"),
            ("overdue", "Overdue"), ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    line_items = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "invoice_number")]
        ordering = ["-issue_date"]


class FeeDiscount(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_discounts")
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name="discounts",
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="discounts")
    discount_type = models.CharField(
        max_length=20,
        choices=[("waiver", "Waiver"), ("scholarship", "Scholarship"), ("sibling", "Sibling"), ("other", "Other")],
        default="waiver",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            (DISCOUNT_PENDING, "Pending"),
            (DISCOUNT_APPROVED, "Approved"),
            (DISCOUNT_REJECTED, "Rejected"),
        ],
        default=DISCOUNT_PENDING,
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_discounts",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Refund(BaseModel):
    fee_payment = models.ForeignKey(FeePayment, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            (REFUND_PENDING, "Pending"),
            (REFUND_PROCESSED, "Processed"),
            (REFUND_REJECTED, "Rejected"),
        ],
        default=REFUND_PENDING,
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_refunds",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class MiscIncome(BaseModel):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    income_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    account = models.ForeignKey(
        "finance.FinancialAccount", on_delete=models.SET_NULL, null=True, blank=True, related_name="income_entries",
    )
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="recorded_income",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-income_date"]


class FinanceNote(BaseModel):
    content = models.TextField()
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, null=True, blank=True, related_name="finance_notes",
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True, related_name="finance_notes")
    fee_payment = models.ForeignKey(
        FeePayment, on_delete=models.CASCADE, null=True, blank=True, related_name="finance_notes",
    )
    author = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="finance_notes")

    class Meta:
        ordering = ["-created_at"]


class FinancialAccount(BaseModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=[
            ("asset", "Asset"), ("liability", "Liability"),
            ("income", "Income"), ("expense", "Expense"),
        ],
        default="income",
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]


class Budget(BaseModel):
    name = models.CharField(max_length=120)
    academic_year = models.ForeignKey(
        "academics.AcademicYear", on_delete=models.CASCADE, related_name="budgets",
    )
    term = models.ForeignKey("academics.Term", on_delete=models.SET_NULL, null=True, blank=True, related_name="budgets")
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    account = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="budgets")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class AccountingPeriod(BaseModel):
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[(PERIOD_OPEN, "Open"), (PERIOD_CLOSED, "Closed")],
        default=PERIOD_OPEN,
    )
    closed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="closed_periods",
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]


class AccountingEntry(BaseModel):
    entry_date = models.DateField()
    description = models.CharField(max_length=255)
    debit_account = models.CharField(max_length=100)
    credit_account = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    entry_type = models.CharField(
        max_length=20,
        choices=[("expense", "Expense"), ("income", "Income"), ("transfer", "Transfer")],
        default="expense",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=[
            (APPROVAL_PENDING, "Pending"),
            (APPROVAL_APPROVED, "Approved"),
            (APPROVAL_REJECTED, "Rejected"),
        ],
        default=APPROVAL_APPROVED,
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_entries",
    )
    fee_payment = models.ForeignKey(
        FeePayment, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounting_entries",
    )
    account = models.ForeignKey(
        FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="entries",
    )

    class Meta:
        ordering = ["-entry_date"]
        verbose_name_plural = "Accounting entries"