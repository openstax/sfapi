from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0013_active_managers"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="assignable_status",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Assignable Status"),
        ),
        migrations.AddField(
            model_name="account",
            name="assignable_maturity_score",
            field=models.IntegerField(blank=True, null=True, verbose_name="Assignable Maturity Score"),
        ),
        migrations.AddField(
            model_name="account",
            name="assignments_created",
            field=models.IntegerField(blank=True, null=True, verbose_name="Assignments Created"),
        ),
        migrations.AddField(
            model_name="account",
            name="assignments_completed",
            field=models.IntegerField(blank=True, null=True, verbose_name="Assignments Completed"),
        ),
    ]
