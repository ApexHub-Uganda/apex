"""Transport models."""
from django.db import models
from apps.core.models import BaseModel

class Vehicle(BaseModel):
    registration_number = models.CharField(max_length=20)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    vehicle_type = models.CharField(max_length=20, choices=[("bus","Bus"),("van","Van"),("minibus","Minibus")], default="bus")
    status = models.CharField(max_length=20, choices=[("active","Active"),("maintenance","Maintenance"),("retired","Retired")], default="active")
    insurance_expiry = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("tenant", "registration_number")]

class Driver(BaseModel):
    staff = models.OneToOneField("staff.Staff", on_delete=models.CASCADE, related_name="driver_profile")
    license_number = models.CharField(max_length=50)
    license_expiry = models.DateField()
    years_experience = models.PositiveIntegerField(default=0)

class Route(BaseModel):
    name = models.CharField(max_length=100)
    start_point = models.CharField(max_length=255)
    end_point = models.CharField(max_length=255)
    stops = models.JSONField(default=list, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="routes")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="routes")
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ["name"]

class StudentTransport(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="transport_assignments")
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="student_assignments")
    pickup_point = models.CharField(max_length=255)
    dropoff_point = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("active","Active"),("inactive","Inactive")], default="active")

    class Meta:
        ordering = ["-start_date"]
