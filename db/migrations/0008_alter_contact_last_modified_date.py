# Generated by Django 5.0.2 on 2024-06-07 20:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0007_alter_contact_subject_interest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='last_modified_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Last Modified Date'),
        ),
    ]