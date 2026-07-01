"""Inventory models."""
from django.db import models
from apps.core.models import BaseModel

class Item(BaseModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, db_index=True)
    category = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="pcs")
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "sku")]
        ordering = ["name"]

class StockMovement(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=[("in","Stock In"),("out","Stock Out"),("adjustment","Adjustment")])
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-created_at"]

class Procurement(BaseModel):
    title = models.CharField(max_length=255)
    items = models.JSONField(default=list)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    supplier = models.CharField(max_length=255, blank=True)
    order_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("draft","Draft"),("ordered","Ordered"),("received","Received"),("cancelled","Cancelled")], default="draft")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="approved_procurements")

    class Meta:
        ordering = ["-order_date"]
