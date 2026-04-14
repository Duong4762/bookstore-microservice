from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='variantmodel',
            name='cover_image_url',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
    ]
