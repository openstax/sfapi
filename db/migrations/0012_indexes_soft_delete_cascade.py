from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0011_account_local_create_date_account_local_update_date_and_more'),
    ]

    operations = [
        # Add is_deleted fields for soft-delete
        migrations.AddField(
            model_name='account',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='book',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contact',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),

        # Fix on_delete: DO_NOTHING -> CASCADE for Adoption FKs
        migrations.AlterField(
            model_name='adoption',
            name='contact',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='db.contact'),
        ),
        migrations.AlterField(
            model_name='adoption',
            name='opportunity',
            field=models.ForeignKey(max_length=18, on_delete=django.db.models.deletion.CASCADE, to='db.opportunity'),
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['name'], name='idx_account_name'),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['last_modified_date'], name='idx_account_last_mod'),
        ),
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(fields=['accounts_uuid'], name='idx_contact_uuid'),
        ),
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(fields=['accounts_id'], name='idx_contact_accounts_id'),
        ),
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(fields=['email'], name='idx_contact_email'),
        ),
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(fields=['last_modified_date'], name='idx_contact_last_mod'),
        ),
        migrations.AddIndex(
            model_name='adoption',
            index=models.Index(fields=['contact'], name='idx_adoption_contact'),
        ),
        migrations.AddIndex(
            model_name='opportunity',
            index=models.Index(fields=['contact'], name='idx_opp_contact'),
        ),
        migrations.AddIndex(
            model_name='opportunity',
            index=models.Index(fields=['book'], name='idx_opp_book'),
        ),
        migrations.AddIndex(
            model_name='opportunity',
            index=models.Index(fields=['account'], name='idx_opp_account'),
        ),
    ]
