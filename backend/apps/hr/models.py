"""HR models."""
from django.db import models
from apps.core.models import BaseModel

class Leave(BaseModel):
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=20, choices=[("annual","Annual"),("sick","Sick"),("maternity","Maternity"),("paternity","Paternity"),("unpaid","Unpaid"),("other","Other")])
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("cancelled","Cancelled")], default="pending")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leaves")
    approval_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

class PerformanceReview(BaseModel):
    staff = models.ForeignKey("staff.Staff", on_delete=models.CASCADE, related_name="performance_reviews")
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="conducted_reviews")
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1)
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[("draft","Draft"),("submitted","Submitted"),("acknowledged","Acknowledged")], default="draft")

    class Meta:
        ordering = ["-review_period_end"]
