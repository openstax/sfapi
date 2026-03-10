from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_superuser"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "sync_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Kill switch: uncheck to pause all sync management commands.",
                    ),
                ),
                (
                    "api_limit",
                    models.PositiveIntegerField(
                        default=285000,
                        help_text="Salesforce org's daily API call limit.",
                    ),
                ),
                (
                    "pause_threshold",
                    models.FloatField(
                        default=0.85,
                        help_text="Pause syncs when API usage exceeds this fraction of the limit (0.0-1.0).",
                    ),
                ),
                ("last_usage_check", models.DateTimeField(blank=True, editable=False, null=True)),
                ("last_usage_value", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("last_usage_limit", models.PositiveIntegerField(blank=True, editable=False, null=True)),
            ],
            options={
                "verbose_name": "Sync Configuration",
                "verbose_name_plural": "Sync Configuration",
            },
        ),
    ]
