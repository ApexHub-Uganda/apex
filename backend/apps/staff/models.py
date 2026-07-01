"""Staff management models."""
from django.db import models
from apps.core.models import BaseModel

class Staff(BaseModel):
    user = models.OneToOneField("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profile")
    employee_id = models.CharField(max_length=50, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    department = models.ForeignKey("academics.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_members")
    designation = models.CharField(max_length=100)
    date_joined = models.DateField()
    date_left = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, choices=[("full_time","Full Time"),("part_time","Part Time"),("contract","Contract")], default="full_time")
    status = models.CharField(max_length=20, choices=[("active","Active"),("on_leave","On Leave"),("terminated","Terminated")], default="active")
    photo = models.ImageField(upload_to="staff/", blank=True, null=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = [("tenant", "employee_id")]
        ordering = ["last_name", "first_name"]
        indexes = [models.Index(fields=["tenant", "status"])]

class Teacher(BaseModel):
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name="teacher_profile")
    subjects = models.ManyToManyField("academics.Subject", related_name="teachers", blank=True)
    qualification = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    is_class_teacher = models.BooleanField(default=False)

    class Meta:
        ordering = ["staff__last_name"]
