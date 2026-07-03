from django.db import migrations, models


def seed_provider_method_types(apps, schema_editor):
    PaymentProvider = apps.get_model("subscriptions", "PaymentProvider")
    mobile_slugs = {"mpesa", "mtn_momo", "airtel_money", "flutterwave_mm"}
    for provider in PaymentProvider.objects.all():
        if provider.slug in mobile_slugs:
            provider.method_type = "mobile_money"
        else:
            provider.method_type = "card"
        provider.save(update_fields=["method_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0003_schema_alignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentprovider",
            name="method_type",
            field=models.CharField(
                choices=[
                    ("card", "Credit or Debit Card"),
                    ("mobile_money", "Mobile Money"),
                ],
                db_index=True,
                default="card",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("card", "Credit or Debit Card"),
                    ("mobile_money", "Mobile Money"),
                ],
                db_index=True,
                default="card",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="payer_phone",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(seed_provider_method_types, migrations.RunPython.noop),
    ]