import django.db.models.manager
from django.db import migrations
import db.models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0012_indexes_soft_delete_cascade'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='account',
            managers=[
                ('objects', db.models.ActiveManager()),
                ('all_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='book',
            managers=[
                ('objects', db.models.ActiveManager()),
                ('all_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='contact',
            managers=[
                ('objects', db.models.ActiveManager()),
                ('all_objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
