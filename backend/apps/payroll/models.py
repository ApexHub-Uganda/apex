"""Payroll models."""
from decimal import Decimal
from django.db import models
from apps.core.models import BaseModel

class SalaryStructure(BaseModel):
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, related_name="salary_structures")
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.JSONField(default=dict, blank=True)
    deductions = models.JSONField(default=dict, blank=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-effective_from"]

class PayrollRun(BaseModel):
    title = models.CharField(max_length=255)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=[("draft","Draft"),("processing","Processing"),("completed","Completed"),("cancelled","Cancelled")], default="draft")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    processed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="processed_payrolls")
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-period_end"]

class Payslip(BaseModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="payslips")
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, related_name="payslips")
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    breakdown = models.JSONField(default=dict, blank=True)
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("tenant", "payroll_run", "staff")]
        ordering = ["staff__last_name"]
