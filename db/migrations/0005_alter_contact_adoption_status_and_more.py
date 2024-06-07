# Generated by Django 5.0.2 on 2024-06-07 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0004_remove_contact_last_activity_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='adoption_status',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='lead_source',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='lms',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='position',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='reject_reason',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='role',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='signup_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(max_length=128, null=True),
        ),
    ]