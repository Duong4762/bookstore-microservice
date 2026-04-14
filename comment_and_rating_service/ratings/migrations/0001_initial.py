from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("book_id", models.IntegerField()),
                ("customer_id", models.IntegerField()),
                (
                    "rating",
                    models.IntegerField(
                        help_text="Rating từ 1 đến 5 sao",
                        validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)],
                    ),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ratings",
                "ordering": ["-created_at"],
                "unique_together": {("book_id", "customer_id")},
            },
        ),
    ]

