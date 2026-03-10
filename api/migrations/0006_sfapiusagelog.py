from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0005_syncconfig"),
    ]

    operations = [
        migrations.CreateModel(
            name="SFAPIUsageLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                (
                    "source",
                    models.CharField(
                        db_index=True,
                        help_text="What triggered the API call (e.g. sync_accounts, sync_contacts, api_request, limits_check).",
                        max_length=50,
                    ),
                ),
                ("call_count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "SF API Usage Log",
                "verbose_name_plural": "SF API Usage Logs",
                "ordering": ["-date", "source"],
                "unique_together": {("date", "source")},
            },
        ),
    ]
