from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_listing_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="listing_images/"),
        ),
    ]
