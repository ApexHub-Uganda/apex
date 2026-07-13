from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0008_teachingassignment"),
        ("examinations", "0004_gradingscheme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="exam",
            name="exam_type",
            field=models.CharField(
                choices=[
                    ("midterm", "Midterm"),
                    ("final", "Final"),
                    ("continuous", "Continuous Assessment"),
                    ("assignment", "Class Assignment"),
                ],
                default="final",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="exam",
            name="term",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional for class assignments tracked outside term examinations",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="exams",
                to="academics.term",
            ),
        ),
    ]