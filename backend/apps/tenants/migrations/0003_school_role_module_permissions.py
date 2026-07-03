"""School role module permissions."""
from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_registration_notifications"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchoolRoleModulePermission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[
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
                ], db_index=True, max_length=30)),
                ("module_key", models.CharField(db_index=True, max_length=50)),
                ("can_read", models.BooleanField(default=False)),
                ("can_write", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="role_module_permissions",
                    to="tenants.tenant",
                )),
            ],
            options={
                "ordering": ["role", "module_key"],
            },
        ),
        migrations.AddIndex(
            model_name="schoolrolemodulepermission",
            index=models.Index(fields=["tenant", "role"], name="tenants_sch_tenant__a8e2c1_idx"),
        ),
        migrations.AddIndex(
            model_name="schoolrolemodulepermission",
            index=models.Index(fields=["tenant", "module_key"], name="tenants_sch_tenant__f4b9d2_idx"),
        ),
        migrations.AddConstraint(
            model_name="schoolrolemodulepermission",
            constraint=models.UniqueConstraint(
                fields=("tenant", "role", "module_key"),
                name="uniq_tenant_role_module_permission",
            ),
        ),
    ]