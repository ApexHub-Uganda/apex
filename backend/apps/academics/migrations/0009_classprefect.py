# Generated manually for ClassPrefect model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("academics", "0008_teachingassignment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassPrefect",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("role", models.CharField(
                    choices=[
                        ("head", "Head Prefect"),
                        ("deputy", "Deputy Prefect"),
                        ("prefect", "Prefect"),
                    ],
                    default="prefect",
                    max_length=20,
                )),
                ("appointed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="appointed_prefects",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="%(class)s_created",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("school_class", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="prefects",
                    to="academics.class",
                )),
                ("stream", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="prefects",
                    to="academics.stream",
                )),
                ("student", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="prefect_roles",
                    to="students.student",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="%(class)s_set",
                    to="tenants.tenant",
                )),
                ("updated_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="%(class)s_updated",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "class prefect",
                "ordering": ["role", "student__last_name", "student__first_name"],
            },
        ),
        migrations.AddIndex(
            model_name="classprefect",
            index=models.Index(fields=["tenant", "school_class"], name="academics_c_tenant__8f0e2a_idx"),
        ),
        migrations.AddIndex(
            model_name="classprefect",
            index=models.Index(fields=["tenant", "stream"], name="academics_c_tenant__a41c8d_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="classprefect",
            unique_together={("tenant", "student", "school_class", "stream")},
        ),
    ]