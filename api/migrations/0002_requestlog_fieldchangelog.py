from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("method", models.CharField(max_length=10)),
                ("path", models.CharField(max_length=2048)),
                ("query_params", models.JSONField(blank=True, default=dict)),
                ("auth_type", models.CharField(blank=True, max_length=20)),
                ("auth_identifier", models.CharField(blank=True, max_length=255)),
                ("status_code", models.IntegerField()),
                ("duration_ms", models.IntegerField()),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=512)),
            ],
            options={
                "verbose_name": "Request Log",
                "verbose_name_plural": "Request Logs",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["path"], name="idx_reqlog_path"),
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["auth_type"], name="idx_reqlog_auth_type"),
        ),
        migrations.CreateModel(
            name="FieldChangeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("model_name", models.CharField(max_length=100)),
                ("record_id", models.CharField(max_length=255)),
                ("field_name", models.CharField(max_length=100)),
                ("old_value", models.TextField(blank=True, null=True)),
                ("new_value", models.TextField(blank=True, null=True)),
                (
                    "change_source",
                    models.CharField(
                        choices=[("api", "API"), ("sync", "Sync"), ("admin", "Admin")], default="api", max_length=20
                    ),
                ),
                ("changed_by", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Field Change Log",
                "verbose_name_plural": "Field Change Logs",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="fieldchangelog",
            index=models.Index(fields=["model_name", "record_id"], name="idx_changelog_model_record"),
        ),
    ]
