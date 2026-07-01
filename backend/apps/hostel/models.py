"""Hostel models."""
from django.db import models
from apps.core.models import BaseModel

class Hostel(BaseModel):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=[("male","Male"),("female","Female"),("mixed","Mixed")])
    warden = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_hostels")
    address = models.TextField(blank=True)
    total_rooms = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

class Room(BaseModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    floor = models.PositiveSmallIntegerField(default=1)
    capacity = models.PositiveIntegerField(default=4)
    occupied = models.PositiveIntegerField(default=0)
    room_type = models.CharField(max_length=20, choices=[("single","Single"),("double","Double"),("dormitory","Dormitory")], default="dormitory")
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = [("tenant", "hostel", "room_number")]
        ordering = ["hostel", "room_number"]

class Allocation(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="hostel_allocations")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="allocations")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("active","Active"),("vacated","Vacated")], default="active")
    bed_number = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ["-start_date"]
