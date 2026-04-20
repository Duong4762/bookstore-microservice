from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("carts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="variant_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="cartitem",
            unique_together={("cart", "book_id", "variant_id")},
        ),
    ]

