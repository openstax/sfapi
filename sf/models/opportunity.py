from salesforce import models
from .book import Book
from .account import Account
from .contact import Contact

class Opportunity(models.SalesforceModel):
    account = models.ForeignKey(Account, models.DO_NOTHING, db_column='AccountId', max_length=18, verbose_name='Account ID', blank=True, null=True)  # References to missing tables: ['-Account']
    record_type_id = models.CharField(db_column='RecordTypeId', max_length=18, verbose_name='Record Type ID', blank=True, null=True)  # References to missing tables: ['-RecordType']
    name = models.CharField(db_column='Name', max_length=120)
    description = models.TextField(db_column='Description', blank=True, null=True)
    stage_name = models.CharField(db_column='StageName', max_length=255, verbose_name='Stage', choices=[('Confirmed Adoption Won', 'Confirmed Adoption Won'), ('Closed Lost', 'Closed Lost'), ('Unconfirmed', 'Unconfirmed'), ('Lapsed - Book Used Previously Not Currently', 'Lapsed - Book Used Previously Not Currently'), ('Inactive - Book No Longer in Use', 'Inactive - Book No Longer in Use'), ('Assumed - Book Likely in Use', 'Assumed - Book Likely in Use'), ('Active - Book Currently in Use', 'Active - Book Currently in Use')])
    amount = models.DecimalField(db_column='Amount', max_digits=18, decimal_places=2, verbose_name='Savings: Current', blank=True, null=True)
    probability = models.DecimalField(db_column='Probability', max_digits=3, decimal_places=0, verbose_name='Probability (%)', default=models.DEFAULTED_ON_CREATE, blank=True, null=True)
    close_date = models.DateField(db_column='CloseDate', verbose_name='Confirm Date', help_text='IF Type = Renewal > Date this was renewed\r\nIF Type = Renewal Verified > Date this was verified\r\nIF Type = New Business > Date this was closed (won)')
    type = models.CharField(db_column='Type', max_length=255, verbose_name='Opportunity Type', default='New Business', choices=[('Renewal', 'Renewal'), ('New Business', 'New Business'), ('Renewal - Verified', 'Renewal - Verified')], blank=True, null=True)
    lead_source = models.CharField(db_column='LeadSource', max_length=255, choices=[('Customer Service Ticket', 'Customer Service Ticket'), ('Phone', 'Phone'), ('Chat', 'Chat'), ('Conference', 'Conference'), ('Comp Request', 'Comp Request'), ('Partner', 'Partner'), ('Newsletter', 'Newsletter'), ('Adoption Form', 'Adoption Form'), ('Referral Form', 'Referral Form'), ('Renewal Form', 'Renewal Form'), ('Donation', 'Donation'), ('Web', 'Web'), ('Webinar', 'Webinar'), ('Institutional Relations', 'Institutional Relations'), ('Followup Form', 'Followup Form'), ('Student', 'Student'), ('Email', 'Email'), ('Tutor Signup', 'Tutor Signup'), ('Interest Form', 'Interest Form'), ('Rover', 'Rover'), ('Testimonial', 'Testimonial'), ('Renewal Popup', 'Renewal Popup'), ('Partner Marketplace', 'Partner Marketplace'), ('Offsite Go-To-Webinar Form', 'Offsite Go-To-Webinar Form'), ('Website Tutor Webinar Form', 'Website Tutor Webinar Form'), ('Offsite Creator Feast Registration Form', 'Offsite Creator Feast Registration Form'), ('Manual List Adds', 'Manual List Adds'), ('Website E-Newsletter Sign-Up Form', 'Website E-Newsletter Sign-Up Form'), ('Website Institutional Partner Sign Up Form', 'Website Institutional Partner Sign Up Form'), ('Website Contact Us Form', 'Website Contact Us Form'), ('TSR', 'TSR'), ('Facebook Ads', 'Facebook Ads'), ('LinkedIn Ads', 'LinkedIn Ads'), ('BMG Import', 'BMG Import'), ('Account Creation', 'Account Creation')], blank=True, null=True)
    is_closed = models.BooleanField(db_column='IsClosed', verbose_name='Closed', sf_read_only=models.READ_ONLY, default=False)
    is_won = models.BooleanField(db_column='IsWon', verbose_name='Won', sf_read_only=models.READ_ONLY, default=False)
    owner_id = models.CharField(db_column='OwnerId', max_length=18, verbose_name='Owner ID', default=models.DEFAULTED_ON_CREATE)  # References to missing tables: ['-User']
    created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=models.READ_ONLY)
    created_by_id = models.CharField(db_column='CreatedById', max_length=18, verbose_name='Created By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=models.READ_ONLY)
    last_modified_by_id = models.CharField(db_column='LastModifiedById', max_length=18, verbose_name='Last Modified By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    system_modstamp = models.DateTimeField(db_column='SystemModstamp', sf_read_only=models.READ_ONLY)
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_activity_in_days = models.IntegerField(db_column='LastActivityInDays', verbose_name='Recent Activity', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_stage_change_date = models.DateTimeField(db_column='LastStageChangeDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_stage_change_in_days = models.IntegerField(db_column='LastStageChangeInDays', verbose_name='Days In Stage', sf_read_only=models.READ_ONLY, blank=True, null=True)
    fiscal_year = models.IntegerField(db_column='FiscalYear', sf_read_only=models.READ_ONLY, blank=True, null=True)
    fiscal = models.CharField(db_column='Fiscal', max_length=6, verbose_name='Fiscal Period', sf_read_only=models.READ_ONLY, blank=True, null=True)
    contact = models.ForeignKey(Contact, models.DO_NOTHING, db_column='ContactId', max_length=18, verbose_name='Contact ID', sf_read_only=models.NOT_UPDATEABLE, blank=True, null=True)  # References to missing tables: ['-Contact']
    last_viewed_date = models.DateTimeField(db_column='LastViewedDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_referenced_date = models.DateTimeField(db_column='LastReferencedDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    book = models.ForeignKey(Book, models.DO_NOTHING, db_column='Book__c', max_length=18, blank=True, null=True)  # References to missing tables: ['-Book__c']

    class Meta(models.Model.Meta):
        db_table = 'Opportunity'
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
        # keyPrefix = '006'
