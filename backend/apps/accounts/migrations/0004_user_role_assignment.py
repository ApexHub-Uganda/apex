# Generated manually for dual portal roles

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_must_change_password"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserRoleAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("super_admin", "Super Admin"),
                            ("school_admin", "School Admin"),
                            ("head_teacher", "Head Teacher"),
                            ("deputy_head_teacher", "Deputy Head Teacher"),
                            ("director_of_studies", "Director of Studies"),
                            ("head_of_department", "Head of Department"),
                            ("teacher", "Teacher"),
                            ("class_teacher", "Class Teacher"),
                            ("parent", "Parent"),
                            ("student", "Student"),
                            ("bursar", "Bursar / Accountant"),
                            ("assistant_bursar", "Assistant Bursar"),
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
                        max_length=30,
                    ),
                ),
                (
                    "is_primary",
                    models.BooleanField(
                        default=False,
                        help_text="Default role restored at login when multiple roles exist.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "source",
                    models.CharField(
                        blank=True,
                        default="admin",
                        help_text="How this role was granted: admin | staff_onboard | parent_link | system",
                        max_length=30,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="roles_granted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_role_assignments",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-is_primary", "role"],
            },
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(fields=["tenant", "role"], name="accounts_us_tenant__dual_r_idx"),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(fields=["user", "is_active"], name="accounts_us_user_id_dual_a_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="userroleassignment",
            unique_together={("user", "tenant", "role")},
        ),
    ]
