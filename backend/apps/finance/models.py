"""Finance models."""
from decimal import Decimal
from django.db import models
from apps.core.models import BaseModel

class FeeStructure(BaseModel):
    name = models.CharField(max_length=255)
    school_class = models.ForeignKey("academics.Class", on_delete=models.CASCADE, related_name="fee_structures")
    term = models.ForeignKey("academics.Term", on_delete=models.CASCADE, related_name="fee_structures")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["due_date"]

class FeePayment(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_payments")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="payments")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=[("cash","Cash"),("bank","Bank Transfer"),("mpesa","M-Pesa"),("card","Card"),("cheque","Cheque")], default="cash")
    reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="received_payments")
    status = models.CharField(max_length=20, choices=[("pending","Pending"),("completed","Completed"),("failed","Failed"),("refunded","Refunded")], default="completed")
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
    status = models.CharField(max_length=20, choices=[("draft","Draft"),("sent","Sent"),("paid","Paid"),("overdue","Overdue"),("cancelled","Cancelled")], default="draft")
    line_items = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "invoice_number")]
        ordering = ["-issue_date"]

class AccountingEntry(BaseModel):
    entry_date = models.DateField()
    description = models.CharField(max_length=255)
    debit_account = models.CharField(max_length=100)
    credit_account = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    fee_payment = models.ForeignKey(FeePayment, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounting_entries")

    class Meta:
        ordering = ["-entry_date"]
        verbose_name_plural = "Accounting entries"
