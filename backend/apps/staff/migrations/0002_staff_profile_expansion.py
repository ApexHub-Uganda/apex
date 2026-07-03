"""Expand staff profile for robust HR onboarding."""
from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="staff",
            name="middle_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="staff",
            name="personal_email",
            field=models.EmailField(blank=True, help_text="Personal / alternate email", max_length=254),
        ),
        migrations.AddField(
            model_name="staff",
            name="alternate_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="staff",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="national_id",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="staff",
            name="nationality",
            field=models.CharField(default="Kenyan", max_length=100),
        ),
        migrations.AddField(
            model_name="staff",
            name="staff_category",
            field=models.CharField(
                choices=[
                    ("management", "Management"),
                    ("teaching", "Teaching"),
                    ("administrative", "Administrative"),
                    ("support", "Support"),
                    ("finance", "Finance"),
                ],
                default="administrative",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="portal_role",
            field=models.CharField(
                choices=[
                    ("super_admin", "Super Admin"),
                    ("school_admin", "School Admin"),
                    ("head_teacher", "Head Teacher"),
                    ("deputy_head_teacher", "Deputy Head Teacher"),
                    ("director_of_studies", "Director of Studies"),
                    ("head_of_department", "Head of Department"),
                    ("teacher", "Teacher"),
                    ("parent", "Parent"),
                    ("student", "Student"),
                    ("bursar", "Bursar / Accountant"),
                    ("librarian", "Librarian"),
                    ("hr_manager", "Human Resource Manager"),
                    ("transport_manager", "Transport Manager"),
                    ("hostel_manager", "Hostel Manager"),
                    ("inventory_manager", "Inventory Manager / Store Keeper"),
                    ("finance_officer", "Finance Officer (Legacy)"),
                    ("hr_officer", "HR Officer (Legacy)"),
                    ("transport_officer", "Transport Officer (Legacy)"),
                    ("hostel_warden", "Hostel Warden (Legacy)"),
                    ("inventory_officer", "Inventory Officer (Legacy)"),
                    ("receptionist", "Receptionist"),
                    ("nurse", "Nurse"),
                    ("counselor", "Counselor"),
                ],
                db_index=True,
                default="teacher",
                help_text="Dashboard role assigned when portal access is enabled",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="supervisor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="direct_reports",
                to="staff.staff",
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="emergency_relationship",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="staff",
            name="has_portal_access",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="qualification_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="staff",
            name="email",
            field=models.EmailField(help_text="Primary work email — used for portal login when enabled", max_length=254),
        ),
        migrations.AlterField(
            model_name="staff",
            name="employment_type",
            field=models.CharField(
                choices=[
                    ("full_time", "Full Time"),
                    ("part_time", "Part Time"),
                    ("contract", "Contract"),
                    ("intern", "Intern"),
                ],
                default="full_time",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="staff",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("on_leave", "On Leave"),
                    ("suspended", "Suspended"),
                    ("terminated", "Terminated"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["tenant", "portal_role"], name="staff_staff_tenant__4a1c2e_idx"),
        ),
        migrations.AddIndex(
            model_name="staff",
            index=models.Index(fields=["tenant", "email"], name="staff_staff_tenant__9f3b1a_idx"),
        ),
    ]