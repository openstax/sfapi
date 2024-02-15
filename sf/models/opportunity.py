from salesforce import models
from .book import Book
from .account import Account

class Opportunity(models.SalesforceModel):
    account = models.ForeignKey(Account, models.DO_NOTHING, db_column='AccountId', max_length=18, verbose_name='Account ID', blank=True, null=True)  # References to missing tables: ['-Account']
    record_type_id = models.CharField(db_column='RecordTypeId', max_length=18, verbose_name='Record Type ID', blank=True, null=True)  # References to missing tables: ['-RecordType']
    is_private = models.BooleanField(db_column='IsPrivate', verbose_name='Private', default=False)
    name = models.CharField(db_column='Name', max_length=120)
    description = models.TextField(db_column='Description', blank=True, null=True)
    stage_name = models.CharField(db_column='StageName', max_length=255, verbose_name='Stage', choices=[('Confirmed Adoption Won', 'Confirmed Adoption Won'), ('Closed Lost', 'Closed Lost'), ('Unconfirmed', 'Unconfirmed'), ('Lapsed - Book Used Previously Not Currently', 'Lapsed - Book Used Previously Not Currently'), ('Inactive - Book No Longer in Use', 'Inactive - Book No Longer in Use'), ('Assumed - Book Likely in Use', 'Assumed - Book Likely in Use'), ('Active - Book Currently in Use', 'Active - Book Currently in Use')])
    amount = models.DecimalField(db_column='Amount', max_digits=18, decimal_places=2, verbose_name='Savings: Current', blank=True, null=True)
    probability = models.DecimalField(db_column='Probability', max_digits=3, decimal_places=0, verbose_name='Probability (%)', default=models.DEFAULTED_ON_CREATE, blank=True, null=True)
    expected_revenue = models.DecimalField(db_column='ExpectedRevenue', max_digits=18, decimal_places=2, verbose_name='Expected Amount', sf_read_only=models.READ_ONLY, blank=True, null=True)
    total_opportunity_quantity = models.DecimalField(db_column='TotalOpportunityQuantity', max_digits=18, decimal_places=2, verbose_name='Quantity', blank=True, null=True)
    close_date = models.DateField(db_column='CloseDate', verbose_name='Confirm Date', help_text='IF Type = Renewal > Date this was renewed\r\nIF Type = Renewal Verified > Date this was verified\r\nIF Type = New Business > Date this was closed (won)')
    type = models.CharField(db_column='Type', max_length=255, verbose_name='Opportunity Type', default='New Business', choices=[('Renewal', 'Renewal'), ('New Business', 'New Business'), ('Renewal - Verified', 'Renewal - Verified')], blank=True, null=True)
    next_step = models.CharField(db_column='NextStep', max_length=255, blank=True, null=True)
    lead_source = models.CharField(db_column='LeadSource', max_length=255, choices=[('Customer Service Ticket', 'Customer Service Ticket'), ('Phone', 'Phone'), ('Chat', 'Chat'), ('Conference', 'Conference'), ('Comp Request', 'Comp Request'), ('Partner', 'Partner'), ('Newsletter', 'Newsletter'), ('Adoption Form', 'Adoption Form'), ('Referral Form', 'Referral Form'), ('Renewal Form', 'Renewal Form'), ('Donation', 'Donation'), ('Web', 'Web'), ('Webinar', 'Webinar'), ('Institutional Relations', 'Institutional Relations'), ('Followup Form', 'Followup Form'), ('Student', 'Student'), ('Email', 'Email'), ('Tutor Signup', 'Tutor Signup'), ('Interest Form', 'Interest Form'), ('Rover', 'Rover'), ('Testimonial', 'Testimonial'), ('Renewal Popup', 'Renewal Popup'), ('Partner Marketplace', 'Partner Marketplace'), ('Offsite Go-To-Webinar Form', 'Offsite Go-To-Webinar Form'), ('Website Tutor Webinar Form', 'Website Tutor Webinar Form'), ('Offsite Creator Feast Registration Form', 'Offsite Creator Feast Registration Form'), ('Manual List Adds', 'Manual List Adds'), ('Website E-Newsletter Sign-Up Form', 'Website E-Newsletter Sign-Up Form'), ('Website Institutional Partner Sign Up Form', 'Website Institutional Partner Sign Up Form'), ('Website Contact Us Form', 'Website Contact Us Form'), ('TSR', 'TSR'), ('Facebook Ads', 'Facebook Ads'), ('LinkedIn Ads', 'LinkedIn Ads'), ('BMG Import', 'BMG Import'), ('Account Creation', 'Account Creation')], blank=True, null=True)
    is_closed = models.BooleanField(db_column='IsClosed', verbose_name='Closed', sf_read_only=models.READ_ONLY, default=False)
    is_won = models.BooleanField(db_column='IsWon', verbose_name='Won', sf_read_only=models.READ_ONLY, default=False)
    forecast_category = models.CharField(db_column='ForecastCategory', max_length=40, sf_read_only=models.READ_ONLY, choices=[('Omitted', 'Omitted'), ('Pipeline', 'Pipeline'), ('BestCase', 'Best Case'), ('MostLikely', 'Most Likely'), ('Forecast', 'Commit'), ('Closed', 'Closed')])
    forecast_category_name = models.CharField(db_column='ForecastCategoryName', max_length=255, verbose_name='Forecast Category', default=models.DEFAULTED_ON_CREATE, choices=[('Omitted', 'Omitted'), ('Pipeline', 'Pipeline'), ('Best Case', 'Best Case'), ('Commit', 'Commit'), ('Closed', 'Closed')], blank=True, null=True)
    campaign_id = models.CharField(db_column='CampaignId', max_length=18, verbose_name='Campaign ID', blank=True, null=True)  # References to missing tables: ['-Campaign']
    has_opportunity_line_item = models.BooleanField(db_column='HasOpportunityLineItem', verbose_name='Has Line Item', sf_read_only=models.READ_ONLY, default=False)
    pricebook2_id = models.CharField(db_column='Pricebook2Id', max_length=18, verbose_name='Price Book ID', default=models.DEFAULTED_ON_CREATE, blank=True, null=True)  # References to missing tables: ['-Pricebook2']
    owner_id = models.CharField(db_column='OwnerId', max_length=18, verbose_name='Owner ID', default=models.DEFAULTED_ON_CREATE)  # References to missing tables: ['-User']
    created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=models.READ_ONLY)
    age_in_days = models.IntegerField(db_column='AgeInDays', verbose_name='Age', sf_read_only=models.READ_ONLY, blank=True, null=True)
    created_by_id = models.CharField(db_column='CreatedById', max_length=18, verbose_name='Created By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=models.READ_ONLY)
    last_modified_by_id = models.CharField(db_column='LastModifiedById', max_length=18, verbose_name='Last Modified By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    system_modstamp = models.DateTimeField(db_column='SystemModstamp', sf_read_only=models.READ_ONLY)
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_activity_in_days = models.IntegerField(db_column='LastActivityInDays', verbose_name='Recent Activity', sf_read_only=models.READ_ONLY, blank=True, null=True)
    push_count = models.IntegerField(db_column='PushCount', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_stage_change_date = models.DateTimeField(db_column='LastStageChangeDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_stage_change_in_days = models.IntegerField(db_column='LastStageChangeInDays', verbose_name='Days In Stage', sf_read_only=models.READ_ONLY, blank=True, null=True)
    fiscal_quarter = models.IntegerField(db_column='FiscalQuarter', sf_read_only=models.READ_ONLY, blank=True, null=True)
    fiscal_year = models.IntegerField(db_column='FiscalYear', sf_read_only=models.READ_ONLY, blank=True, null=True)
    fiscal = models.CharField(db_column='Fiscal', max_length=6, verbose_name='Fiscal Period', sf_read_only=models.READ_ONLY, blank=True, null=True)
    contact_id = models.CharField(db_column='ContactId', max_length=18, verbose_name='Contact ID', sf_read_only=models.NOT_UPDATEABLE, blank=True, null=True)  # References to missing tables: ['-Contact']
    last_viewed_date = models.DateTimeField(db_column='LastViewedDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    last_referenced_date = models.DateTimeField(db_column='LastReferencedDate', sf_read_only=models.READ_ONLY, blank=True, null=True)
    partner_account_id = models.CharField(db_column='PartnerAccountId', max_length=18, verbose_name='Partner Account ID', sf_read_only=models.READ_ONLY, blank=True, null=True)  # References to missing tables: ['-Account']
    contract_id = models.CharField(db_column='ContractId', max_length=18, verbose_name='Contract ID', blank=True, null=True)  # References to missing tables: ['-Contract']
    has_open_activity = models.BooleanField(db_column='HasOpenActivity', sf_read_only=models.READ_ONLY, default=False)
    has_overdue_task = models.BooleanField(db_column='HasOverdueTask', sf_read_only=models.READ_ONLY, default=False)
    is_priority_record = models.BooleanField(db_column='IsPriorityRecord', verbose_name='Important', sf_read_only=models.READ_ONLY, default=False)
    department_adoption = models.BooleanField(db_column='Department_Adoption__c', verbose_name='Department Adoption', default=False)
    students_all_time = models.DecimalField(db_column='Students_All_Time__c', max_digits=18, decimal_places=0, verbose_name='Students All Time', sf_read_only=models.READ_ONLY, blank=True, null=True)
    students_current_year = models.DecimalField(db_column='Students_Current_Year__c', max_digits=18, decimal_places=0, verbose_name='Students Current Year', default=0, blank=True, null=True)
    savings_all_time = models.DecimalField(db_column='Savings_All_Time__c', max_digits=18, decimal_places=2, verbose_name='Savings: All Time', sf_read_only=models.READ_ONLY, blank=True, null=True)
    reason_lost = models.CharField(db_column='Reason_Lost__c', max_length=255, verbose_name='Reason Lost', choices=[('Course Not Offered', 'Course Not Offered'), ('Dissatisfied', 'Dissatisfied'), ('No online HW available', 'No online HW available'), ('Not Teaching', 'Not Teaching'), ("Won't Charge Students", "Won't Charge Students"), ('Using Competitor', 'Using Competitor'), ('Other', 'Other'), ('LIT >3 years ago', 'LIT >3 years ago')], blank=True, null=True)
    need_rollup = models.BooleanField(db_column='Need_Rollup__c', verbose_name='Need Rollup', default=False)
    base_year = models.DecimalField(db_column='Base_Year__c', max_digits=18, decimal_places=0, verbose_name='Base Year', sf_read_only=models.READ_ONLY, blank=True, null=True)
    department_name = models.CharField(db_column='Department_Name__c', max_length=255, verbose_name='Department Name', blank=True, null=True)
    department_opportunity = models.ForeignKey('self', models.DO_NOTHING, db_column='Department_Opportunity__c', verbose_name='Department Opportunity', blank=True, null=True)
    school_year_of_first_adoption = models.DecimalField(db_column='School_Year_of_First_Adoption__c', max_digits=4, decimal_places=0, verbose_name='School Year of First Adoption', sf_read_only=models.READ_ONLY, blank=True, null=True)
    school_year = models.CharField(db_column='School_Year__c', max_length=1300, verbose_name='School Year', sf_read_only=models.READ_ONLY, blank=True, null=True)
    school_year_of_latest_adoption = models.DecimalField(db_column='School_Year_of_Latest_Adoption__c', max_digits=4, decimal_places=0, verbose_name='School Year of Latest Adoption', sf_read_only=models.READ_ONLY, blank=True, null=True)
    renewal_status = models.CharField(db_column='Renewal_Status__c', max_length=255, verbose_name='Renewal Status', default='Needs Renewal', choices=[('Needs Renewal', 'Needs Renewal'), ('Done Renewed', 'Done Renewed'), ('Dropped', 'Dropped'), ('Needs check', 'Needs check')], blank=True, null=True)
    book = models.ForeignKey(Book, models.DO_NOTHING, db_column='Book__c', max_length=18, blank=True, null=True)  # References to missing tables: ['-Book__c']
    class_start_date = models.DateField(db_column='Class_Start_Date__c', verbose_name='Class Start Date', blank=True, null=True)
    contact = models.CharField(db_column='Contact__c', max_length=18, blank=True, null=True)  # References to missing tables: ['-Contact']
    dup_name_check = models.CharField(db_column='Dup_Name_Check__c', unique=True, max_length=255, verbose_name='Dup Name Check', help_text='Checks for duplicates', blank=True, null=True)
    time_period = models.CharField(db_column='Time_Period__c', max_length=255, verbose_name='Time Period', choices=[('Semester', 'Semester'), ('Year', 'Year')], blank=True, null=True)
    trigger_rollup = models.BooleanField(db_column='Trigger_Rollup__c', verbose_name='Trigger Rollup', default=False)
    sort = models.CharField(db_column='sort__c', max_length=1300, verbose_name='sort', sf_read_only=models.READ_ONLY, blank=True, null=True)
    school_type = models.CharField(db_column='School_Type__c', max_length=1300, verbose_name='School Type', sf_read_only=models.READ_ONLY, blank=True, null=True)
    contact_name = models.CharField(db_column='Contact_Name__c', max_length=1300, verbose_name='Contact Name', sf_read_only=models.READ_ONLY, blank=True, null=True)
    school_name = models.CharField(db_column='School_Name__c', max_length=1300, verbose_name='School Name', sf_read_only=models.READ_ONLY, blank=True, null=True)
    students_okay = models.BooleanField(db_column='Students_Okay__c', verbose_name='Students Okay', default=False)

    class Meta(models.Model.Meta):
        db_table = 'Opportunity'
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
        # keyPrefix = '006'
