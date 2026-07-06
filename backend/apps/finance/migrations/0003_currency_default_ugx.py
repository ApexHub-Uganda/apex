from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_ea_context_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feestructure",
            name="currency",
            field=models.CharField(default="UGX", max_length=3),
        ),
    ]