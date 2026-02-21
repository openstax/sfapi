from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Human-readable name for this key.', max_length=100)),
                ('key_prefix', models.CharField(help_text='First 8 chars of the key for identification.', max_length=8)),
                ('key_hash', models.CharField(help_text='SHA-256 hash of the full key.', max_length=64)),
                ('scopes', models.JSONField(default=list, help_text="List of permission scopes, e.g. ['read:books', 'write:cases'].")),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.CharField(blank=True, help_text='Who created this key.', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'API Key',
                'verbose_name_plural': 'API Keys',
            },
        ),
    ]
