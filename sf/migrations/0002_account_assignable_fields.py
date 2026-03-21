# Manually written — makemigrations requires SF credentials

import django.db.models.manager
import salesforce.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sf", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="assignable_status",
            field=models.CharField(
                blank=True,
                db_column="Assignable_Status__c",
                max_length=255,
                null=True,
                verbose_name="Assignable Status",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="assignable_maturity_score",
            field=models.DecimalField(
                blank=True,
                db_column="Assignable_Maturity_Score__c",
                decimal_places=0,
                max_digits=5,
                null=True,
                verbose_name="Assignable Maturity Score",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="assignments_created",
            field=models.DecimalField(
                blank=True,
                db_column="Assignments_Created__c",
                decimal_places=0,
                max_digits=18,
                null=True,
                verbose_name="Assignments Created",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="assignments_completed",
            field=models.DecimalField(
                blank=True,
                db_column="Assignments_Completed__c",
                decimal_places=0,
                max_digits=18,
                null=True,
                verbose_name="Assignments Completed",
            ),
        ),
    ]
