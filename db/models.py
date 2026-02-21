from django.db import models
from .tracking import ChangeTrackingMixin


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Account(ChangeTrackingMixin, models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    name = models.CharField(max_length=255, verbose_name='Account Name')
    type = models.CharField(max_length=255, verbose_name='Account Type',
                            choices=[
                                ('College/University (4)', 'College/University (4)'),
                                ('Technical/Community College (2)', 'Technical/Community College (2)'),
                                ('Career School/For-Profit (2)', 'Career School/For-Profit (2)'),
                                ('For-Profit Tutoring', 'For-Profit Tutoring'),
                                ('High School', 'High School'),
                                ('Elementary School', 'Elementary School'),
                                ('Middle/Junior High School', 'Middle/Junior High School'),
                                ('K-12 School', 'K-12 School'), ('Other', 'Other'),
                                ('Research Centers', 'Research Centers'),
                                ('Intergovernmental', 'Intergovernmental'),
                                ('Tutoring', 'Tutoring'),
                                ('Programs', 'Programs'),
                                ('Vendors', 'Vendors'),
                                ('School District', 'School District'),
                                ('Home School', 'Home School'),
                                ('Parent', 'Parent'),
                                ('Vocational', 'Vocational'),
                                ('Child', 'Child')
                            ], blank=True, null=True)
    city = models.CharField(max_length=40, blank=True, null=True)
    state = models.CharField(max_length=80, blank=True, null=True)
    country = models.CharField(max_length=80, blank=True, null=True)
    state_code = models.CharField(max_length=10,  blank=True, null=True)
    country_code = models.CharField(max_length=10, default='US', blank=True, null=True)
    created_date = models.DateTimeField(null=True)
    last_modified_date = models.DateTimeField(null=True)
    last_activity_date = models.DateField(verbose_name='Last Activity', blank=True, null=True)
    lms = models.CharField(max_length=255, verbose_name='LMS',
                           choices=[
                               ('Blackboard', 'Blackboard'),
                               ('Brightspace', 'Brightspace'),
                               ('Canvas', 'Canvas'),
                               ('D2L (Desire2Learn)', 'D2L (Desire2Learn)'),
                               ('Learning Studio', 'Learning Studio'),
                               ('Moodle', 'Moodle'),
                               ('MoodleRooms', 'MoodleRooms'),
                               ('Sakai', 'Sakai'),
                               ('Other', 'Other')
                           ], blank=True, null=True)
    books_adopted = models.TextField(verbose_name='Books Adopted', blank=True, null=True)
    sheer_id_school_name = models.CharField(max_length=255, verbose_name='SheerID School Name', blank=True, null=True)
    ipeds_id = models.CharField(max_length=255, verbose_name='IPEDS ID', blank=True, null=True)
    nces_district_id = models.CharField(max_length=50, blank=True, null=True)
    nces_district_id2 = models.CharField(max_length=50, blank=True, null=True)
    nces_id = models.CharField(max_length=255, verbose_name='NCESID', blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    local_create_date = models.DateTimeField(auto_now_add=True, verbose_name='Local Create Date')
    local_update_date = models.DateTimeField(auto_now=True, verbose_name='Local Update Date')

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        get_latest_by = 'last_modified_date'
        indexes = [
            models.Index(fields=['name'], name='idx_account_name'),
            models.Index(fields=['last_modified_date'], name='idx_account_last_mod'),
        ]

    def __str__(self):
        return self.name

class Book(ChangeTrackingMixin, models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    name = models.CharField(max_length=255)
    official_name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    subject_areas = models.CharField(max_length=255, null=True)
    website_url = models.URLField(max_length=255, null=True)
    active_book = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    local_create_date = models.DateTimeField(auto_now_add=True, verbose_name='Local Create Date')
    local_update_date = models.DateTimeField(auto_now=True, verbose_name='Local Update Date')

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'

    def __str__(self):
        return self.official_name

class Contact(ChangeTrackingMixin, models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    role = models.CharField(max_length=255, null=True)
    position = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=128, null=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name='Account ID', blank=True, null=True)
    adoption_status = models.CharField(max_length=255, null=True)
    adoptions_json = models.TextField(null=True, blank=True)
    verification_status = models.CharField(max_length=255)
    reject_reason = models.CharField(max_length=255, null=True)
    accounts_uuid = models.CharField(max_length=255)
    accounts_id = models.CharField(max_length=255, null=True, help_text='Prioritize using Accounts_UUID__c over this for ox accounts users.')
    signup_date = models.DateTimeField(null=True)
    lead_source = models.CharField(max_length=255, null=True)
    lms = models.CharField(max_length=255, null=True)
    last_modified_date = models.DateTimeField(verbose_name='Last Modified Date', blank=True, null=True)
    subject_interest = models.CharField(max_length=255, verbose_name='Subject Interest', blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    local_create_date = models.DateTimeField(auto_now_add=True, verbose_name='Local Create Date')
    local_update_date = models.DateTimeField(auto_now=True, verbose_name='Local Update Date')

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        get_latest_by = 'last_modified_date'
        indexes = [
            models.Index(fields=['accounts_uuid'], name='idx_contact_uuid'),
            models.Index(fields=['accounts_id'], name='idx_contact_accounts_id'),
            models.Index(fields=['email'], name='idx_contact_email'),
            models.Index(fields=['last_modified_date'], name='idx_contact_last_mod'),
        ]

    def __str__(self):
        return self.full_name


class Opportunity(ChangeTrackingMixin, models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, max_length=18, verbose_name='Account ID', blank=True, null=True)
    record_type_id = models.CharField(max_length=18, verbose_name='Record Type ID', blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    stage_name = models.CharField(max_length=255, verbose_name='Stage', choices=[('Confirmed Adoption Won', 'Confirmed Adoption Won'), ('Closed Lost', 'Closed Lost'), ('Unconfirmed', 'Unconfirmed'), ('Lapsed - Book Used Previously Not Currently', 'Lapsed - Book Used Previously Not Currently'), ('Inactive - Book No Longer in Use', 'Inactive - Book No Longer in Use'), ('Assumed - Book Likely in Use', 'Assumed - Book Likely in Use'), ('Active - Book Currently in Use', 'Active - Book Currently in Use')])
    amount = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='Savings: Current', blank=True, null=True)
    probability = models.DecimalField(max_digits=3, decimal_places=0, verbose_name='Probability (%)', default=0, blank=True, null=True)
    close_date = models.DateField(verbose_name='Confirm Date')
    type = models.CharField(max_length=255, verbose_name='Opportunity Type', default='New Business', choices=[('Renewal', 'Renewal'), ('New Business', 'New Business'), ('Renewal - Verified', 'Renewal - Verified')], blank=True, null=True)
    lead_source = models.CharField(max_length=255, choices=[('Customer Service Ticket', 'Customer Service Ticket'), ('Phone', 'Phone'), ('Chat', 'Chat'), ('Conference', 'Conference'), ('Comp Request', 'Comp Request'), ('Partner', 'Partner'), ('Newsletter', 'Newsletter'), ('Adoption Form', 'Adoption Form'), ('Referral Form', 'Referral Form'), ('Renewal Form', 'Renewal Form'), ('Donation', 'Donation'), ('Web', 'Web'), ('Webinar', 'Webinar'), ('Institutional Relations', 'Institutional Relations'), ('Followup Form', 'Followup Form'), ('Student', 'Student'), ('Email', 'Email'), ('Tutor Signup', 'Tutor Signup'), ('Interest Form', 'Interest Form'), ('Rover', 'Rover'), ('Testimonial', 'Testimonial'), ('Renewal Popup', 'Renewal Popup'), ('Partner Marketplace', 'Partner Marketplace'), ('Offsite Go-To-Webinar Form', 'Offsite Go-To-Webinar Form'), ('Website Tutor Webinar Form', 'Website Tutor Webinar Form'), ('Offsite Creator Feast Registration Form', 'Offsite Creator Feast Registration Form'), ('Manual List Adds', 'Manual List Adds'), ('Website E-Newsletter Sign-Up Form', 'Website E-Newsletter Sign-Up Form'), ('Website Institutional Partner Sign Up Form', 'Website Institutional Partner Sign Up Form'), ('Website Contact Us Form', 'Website Contact Us Form'), ('TSR', 'TSR'), ('Facebook Ads', 'Facebook Ads'), ('LinkedIn Ads', 'LinkedIn Ads'), ('BMG Import', 'BMG Import'), ('Account Creation', 'Account Creation')], blank=True, null=True)
    is_closed = models.BooleanField(verbose_name='Closed', default=False)
    is_won = models.BooleanField(verbose_name='Won', default=False)
    owner_id = models.CharField(max_length=18, verbose_name='Owner ID')
    created_date = models.DateTimeField()
    created_by_id = models.CharField(max_length=18, verbose_name='Created By ID')
    last_modified_date = models.DateTimeField()
    last_modified_by_id = models.CharField(max_length=18, verbose_name='Last Modified By ID')
    system_modstamp = models.DateTimeField()
    last_activity_date = models.DateField(verbose_name='Last Activity', blank=True, null=True)
    last_activity_in_days = models.IntegerField(verbose_name='Recent Activity', blank=True, null=True)
    last_stage_change_date = models.DateTimeField(blank=True, null=True)
    last_stage_change_in_days = models.IntegerField(verbose_name='Days In Stage', blank=True, null=True)
    fiscal_year = models.IntegerField(blank=True, null=True)
    fiscal = models.CharField( max_length=6, verbose_name='Fiscal Period', blank=True, null=True)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, max_length=18, verbose_name='Contact ID', blank=True, null=True)
    last_viewed_date = models.DateTimeField(blank=True, null=True)
    last_referenced_date = models.DateTimeField(blank=True, null=True)
    book = models.ForeignKey(Book, on_delete=models.PROTECT, max_length=18, blank=True, null=True)
    local_create_date = models.DateTimeField(auto_now_add=True, verbose_name='Local Create Date')
    local_update_date = models.DateTimeField(auto_now=True, verbose_name='Local Update Date')

    class Meta:
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
        get_latest_by = 'last_modified_date'
        indexes = [
            models.Index(fields=['contact'], name='idx_opp_contact'),
            models.Index(fields=['book'], name='idx_opp_book'),
            models.Index(fields=['account'], name='idx_opp_account'),
        ]

    def __str__(self):
        return self.name


# A user will have many adoptions, but they represent a single book for a single school year
# The adoption is nested under the opportunity, which is nested under the contact

class Adoption(ChangeTrackingMixin, models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    adoption_number = models.CharField(max_length=80)
    created_date = models.DateTimeField()
    last_modified_date = models.DateTimeField()
    system_modstamp = models.DateTimeField()
    last_activity_date = models.DateField(blank=True, null=True)
    class_start_date = models.DateField(blank=True, null=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, max_length=18)
    confirmation_date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    base_year = models.DecimalField(max_digits=4, decimal_places=0, blank=True, null=True)
    adoption_type = models.CharField(max_length=255, verbose_name='Adoption Type',
                                     choices=[
                                         ('Faculty/Teacher Adoption', 'Faculty/Teacher Adoption'),
                                         ('School Adoption', 'School Adoption')
                                     ])
    students = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    school_year = models.CharField(max_length=9, verbose_name='School Year')
    terms_used = models.CharField(max_length=255, verbose_name='Terms Used',
                                  choices=[
                                      ('Fall', 'Fall'),
                                      ('Spring', 'Spring'),
                                      ('Both', 'Both'),
                                      ('Winter', 'Winter'),
                                      ('Summer', 'Summer')
                                  ], blank=True, null=True)
    confirmation_type = models.CharField(max_length=255,
                                         verbose_name='Confirmation Type', default='OpenStax Confirmed Adoption',
                                         choices=[
                                             ('OpenStax Confirmed Adoption', 'OpenStax Confirmed Adoption'),
                                             ('Third Party Confirmed Adoption', 'Third Party Confirmed Adoption'),
                                             ('User Behavior Informed Adoption', 'User Behavior Informed Adoption')
                                         ])
    how_using = models.CharField(max_length=255, verbose_name='How Using', choices=[
        ('As the core textbook for my course', 'As the core textbook for my course'),
        ('As an optional/recommended textbook for my course', 'As an optional/recommended textbook for my course'),
        ('To teach, tutor, or support students outside of a course setting',
         'To teach, tutor, or support students outside of a course setting'),
        ('For my own knowledge or other work', 'For my own knowledge or other work')
    ], blank=True, null=True)
    savings = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    local_create_date = models.DateTimeField(auto_now_add=True, verbose_name='Local Create Date')
    local_update_date = models.DateTimeField(auto_now=True, verbose_name='Local Update Date')

    class Meta:
        verbose_name = 'Adoption'
        verbose_name_plural = 'Adoptions'
        get_latest_by = 'last_modified_date'
        indexes = [
            models.Index(fields=['contact'], name='idx_adoption_contact'),
        ]

    def __str__(self):
        return self.name
