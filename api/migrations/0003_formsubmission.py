import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_requestlog_fieldchangelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormSubmission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('form_type', models.CharField(max_length=50)),
                ('data', models.JSONField()),
                ('source_url', models.CharField(blank=True, max_length=2048)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('spam', 'Spam')], default='pending', max_length=20)),
                ('sf_record_id', models.CharField(blank=True, max_length=18)),
                ('error_message', models.TextField(blank=True)),
                ('auth_type', models.CharField(blank=True, max_length=20)),
                ('auth_identifier', models.CharField(blank=True, max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Form Submission',
                'verbose_name_plural': 'Form Submissions',
                'ordering': ['-created_at'],
            },
        ),
    ]
