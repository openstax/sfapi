from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_formsubmission"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuperUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accounts_uuid", models.UUIDField(help_text="OpenStax Accounts UUID for this super user.", unique=True)),
                ("name", models.CharField(blank=True, help_text="Human-readable name for identification.", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Super User",
                "verbose_name_plural": "Super Users",
            },
        ),
    ]
