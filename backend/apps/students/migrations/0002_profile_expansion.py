"""Expand parent, student, and guardian records for production completeness."""
from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="parent",
            name="middle_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="parent",
            name="alternate_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="parent",
            name="alternate_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="parent",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="parent",
            name="national_id",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="parent",
            name="employer",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="parent",
            name="relationship_to_student",
            field=models.CharField(
                choices=[
                    ("father", "Father"),
                    ("mother", "Mother"),
                    ("guardian", "Guardian"),
                    ("sponsor", "Sponsor"),
                    ("other", "Other"),
                ],
                default="guardian",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="parent",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="parent",
            name="country",
            field=models.CharField(default="Kenya", max_length=100),
        ),
        migrations.AddField(
            model_name="parent",
            name="preferred_contact_method",
            field=models.CharField(
                choices=[
                    ("email", "Email"),
                    ("phone", "Phone"),
                    ("sms", "SMS"),
                    ("whatsapp", "WhatsApp"),
                ],
                default="email",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="parent",
            name="is_emergency_contact",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="parent",
            name="has_portal_access",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="parent",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="parent",
            name="email",
            field=models.EmailField(help_text="Primary contact email", max_length=254),
        ),
        migrations.AlterField(
            model_name="parent",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="parent_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="middle_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="alternate_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="student",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="religion",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="student",
            name="place_of_birth",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="student",
            name="previous_school",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="student",
            name="national_id",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="student",
            name="emergency_contact_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="emergency_contact_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="student",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="student",
            name="email",
            field=models.EmailField(blank=True, help_text="Student email or parent-monitored address", max_length=254),
        ),
        migrations.AddField(
            model_name="guardian",
            name="alternate_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="guardian",
            name="address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="guardian",
            name="is_emergency_contact",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="guardian",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AddIndex(
            model_name="parent",
            index=models.Index(fields=["tenant", "phone"], name="students_pa_tenant__c4e8a1_idx"),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(fields=["tenant", "email"], name="students_st_tenant__7d2f9b_idx"),
        ),
    ]