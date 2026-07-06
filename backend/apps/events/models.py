"""School events and registrations."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Event(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    target_audience = models.CharField(
        max_length=20,
        choices=[
            ("all", "Everyone"),
            ("students", "Students"),
            ("parents", "Parents"),
            ("staff", "Staff"),
        ],
        default="all",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("published", "Published"),
            ("cancelled", "Cancelled"),
            ("completed", "Completed"),
        ],
        default="draft",
    )
    is_registration_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date"]


class EventRegistration(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, null=True, blank=True, related_name="event_registrations",
    )
    registrant_name = models.CharField(max_length=200)
    registrant_email = models.EmailField(blank=True)
    registrant_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("registered", "Registered"),
            ("attended", "Attended"),
            ("cancelled", "Cancelled"),
        ],
        default="registered",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]