"""Communication models."""
from django.db import models
from apps.core.models import BaseModel

class Announcement(BaseModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    target_audience = models.CharField(max_length=20, choices=[("all","All"),("staff","Staff"),("students","Students"),("parents","Parents")], default="all")
    priority = models.CharField(max_length=10, choices=[("low","Low"),("normal","Normal"),("high","High"),("urgent","Urgent")], default="normal")
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    attachment = models.FileField(upload_to="announcements/", blank=True, null=True)

    class Meta:
        ordering = ["-publish_date"]

class FeedItemDismissal(models.Model):
    """Per-user dismissal of synthetic navbar feed items (ads, system notices)."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="feed_item_dismissals",
    )
    item_id = models.CharField(max_length=120, db_index=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "item_id")]
        indexes = [models.Index(fields=["user", "item_id"])]


class Notification(BaseModel):
    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=[("info","Info"),("warning","Warning"),("success","Success"),("error","Error")], default="info")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "recipient", "is_read"])]

class SMSMessage(BaseModel):
    recipient_phone = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=[("pending","Pending"),("sent","Sent"),("failed","Failed")], default="pending")
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    cost = models.DecimalField(max_digits=6, decimal_places=4, default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS message"

class EmailMessage(BaseModel):
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=[("pending","Pending"),("sent","Sent"),("failed","Failed")], default="pending")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

class Broadcast(BaseModel):
    title = models.CharField(max_length=255)
    message = models.TextField()
    channels = models.JSONField(default=list)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("draft","Draft"),("scheduled","Scheduled"),("sent","Sent")], default="draft")
    recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

class SupportTicket(BaseModel):
    ticket_number = models.CharField(max_length=20, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=[("technical","Technical"),("billing","Billing"),("academic","Academic"),("general","General")], default="general")
    priority = models.CharField(max_length=10, choices=[("low","Low"),("medium","Medium"),("high","High")], default="medium")
    status = models.CharField(max_length=20, choices=[("open","Open"),("in_progress","In Progress"),("resolved","Resolved"),("closed","Closed")], default="open")
    submitted_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="submitted_tickets")
    assigned_to = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")
    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("tenant", "ticket_number")]
        ordering = ["-created_at"]
