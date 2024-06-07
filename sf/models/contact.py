from salesforce import models
from salesforce.models import SalesforceModel, READ_ONLY, NOT_CREATEABLE, DO_NOTHING, DEFAULTED_ON_CREATE
from .account import Account

class Contact(SalesforceModel):
    first_name = models.CharField(max_length=255, db_column='FirstName')
    last_name = models.CharField(max_length=255, db_column='LastName')
    full_name = models.CharField(max_length=255, db_column='Name')
    email = models.EmailField(max_length=255, db_column='Email')
    role = models.CharField(max_length=255, db_column='Role__c')
    position = models.CharField(max_length=255, db_column='Position__c')
    title = models.CharField(max_length=128, db_column='Title')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, sf_read_only=READ_ONLY, db_column='AccountId',
                                verbose_name='Account ID', blank=True, null=True)
    adoption_status = models.CharField(max_length=255, db_column='Adoption_Status__c')
    adoptions_json = models.TextField(db_column='AdoptionsJSON__c')
    verification_status = models.CharField(max_length=255, db_column='FV_Status__c')
    reject_reason = models.CharField(max_length=255, db_column='Reject_Reason__c')
    accounts_uuid = models.CharField(max_length=255, db_column='Accounts_UUID__c')
    accounts_id = models.CharField(max_length=255, db_column='Accounts_ID__c',
                                   help_text='Prioritize using Accounts_UUID__c over this for ox accounts users.')
    signup_date = models.DateTimeField(db_column='Signup_Date__c')
    lead_source = models.CharField(max_length=255, db_column='LeadSource')
    lms = models.CharField(max_length=255, db_column='LMS__c')
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', verbose_name='Last Modified Date', sf_read_only=READ_ONLY, blank=True, null=True)
    subject_interest = models.CharField(db_column='Subject_Interest__c', max_length=255, verbose_name='Subject Interest', blank=True, null=True)

    class Meta(models.Model.Meta):
        db_table = 'Contact'
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
