from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.IntegerField(unique=True)),
                ("tracking_number", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("carrier", models.CharField(blank=True, max_length=100, null=True)),
                ("shipping_address", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("preparing", "Preparing"),
                            ("shipping", "Shipping"),
                            ("delivered", "Delivered"),
                            ("returned", "Returned"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="preparing",
                        max_length=20,
                    ),
                ),
                ("estimated_delivery", models.DateTimeField(blank=True, null=True)),
                ("actual_delivery", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "shipments",
                "ordering": ["-created_at"],
            },
        ),
    ]

