from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0003_ea_context_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="nationality",
            field=models.CharField(default="Ugandan", max_length=100),
        ),
        migrations.AlterField(
            model_name="student",
            name="upi_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Legacy national learner ID (e.g. former NEMIS UPI). Prefer registration_number.",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="registration_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="School/national registration or index number (Uganda UNEB candidate no. when applicable).",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="district",
            field=models.CharField(blank=True, help_text="Home district", max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="house",
            field=models.CharField(blank=True, help_text="Sports/discipline house", max_length=50),
        ),
        migrations.AlterField(
            model_name="student",
            name="curriculum_pathway",
            field=models.CharField(
                blank=True,
                choices=[
                    ("uneb", "UNEB (Uganda)"),
                    ("uganda_cbe", "Uganda Competence-Based"),
                    ("cbc", "CBC (Kenya)"),
                    ("844", "8-4-4"),
                    ("igcse", "IGCSE"),
                    ("ace", "ACE"),
                    ("other", "Other"),
                ],
                default="uneb",
                max_length=30,
            ),
        ),
    ]
