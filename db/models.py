from django.db import models

class Account(models.Model):
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

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'

class Book(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    name = models.CharField(max_length=255)
    official_name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    subject_areas = models.CharField(max_length=255, null=True)
    website_url = models.URLField(max_length=255, null=True)
    active_book = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'

class Contact(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    role = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    title = models.CharField(max_length=128)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name='Account ID', blank=True, null=True)
    adoption_status = models.CharField(max_length=255)
    adoptions_json = models.TextField(null=True, blank=True)
    verification_status = models.CharField(max_length=255)
    reject_reason = models.CharField(max_length=255)
    accounts_uuid = models.CharField(max_length=255)
    accounts_id = models.CharField(max_length=255, help_text='Prioritize using Accounts_UUID__c over this for ox accounts users.')
    signup_date = models.DateTimeField()
    lead_source = models.CharField(max_length=255)
    lms = models.CharField(max_length=255)
    last_activity_date = models.DateField(verbose_name='Last Activity', blank=True, null=True)
    last_modified_by = models.CharField(max_length=255, help_text='This is useful for ignoring integrations user modifications (like b2bma).')
    subject_interest = models.CharField(max_length=4099, verbose_name='Subject Interest', choices=[
        ('Algebra and Trigonometry', 'Algebra and Trigonometry'),
        ('American Government', 'American Government'),
        ('Anatomy & Physiology', 'Anatomy & Physiology'),
        ('Anthropology', 'Anthropology'),
        ('AP Bio', 'AP Bio'),
        ('AP Macro Econ', 'AP Macro Econ'),
        ('AP Micro Econ', 'AP Micro Econ'),
        ('AP Physics', 'AP Physics'),
        ('Astronomy', 'Astronomy'),
        ('Basic College Math', 'Basic College Math'),
        ('Biology', 'Biology'),
        ('Business Ethics', 'Business Ethics'),
        ('Business Law', 'Business Law'),
        ('Business Law I Essentials', 'Business Law I Essentials'),
        ('Business Statistics', 'Business Statistics'),
        ('Calculus', 'Calculus'),
        ('Career Readiness', 'Career Readiness'),
        ('Chem: Atoms First', 'Chem: Atoms First'),
        ('Chemistry', 'Chemistry'),
        ('College Algebra', 'College Algebra'),
        ('College Algebra with Corequisite Support', 'College Algebra with Corequisite Support'),
        ('College Physics (Algebra)', 'College Physics (Algebra)'),
        ('College Success', 'College Success'),
        ('College Success Concise', 'College Success Concise'),
        ('Concepts of Bio (non-majors)', 'Concepts of Bio (non-majors)'),
        ('Contemporary Math', 'Contemporary Math'),
        ('Economics', 'Economics'),
        ('Elementary Algebra', 'Elementary Algebra'),
        ('Entrepreneurship', 'Entrepreneurship'),
        ('Financial Accounting', 'Financial Accounting'),
        ('Finite Algebra', 'Finite Algebra'),
        ('HS Physics', 'HS Physics'),
        ('HS Statistics', 'HS Statistics'),
        ('Intermediate Algebra', 'Intermediate Algebra'),
        ('Introduction to Business', 'Introduction to Business'),
        ('Introduction to Intellectual Property', 'Introduction to Intellectual Property'),
        ('Introduction to Philosophy', 'Introduction to Philosophy'),
        ('Introduction to Political Science', 'Introduction to Political Science'),
        ('Introduction to Sociology', 'Introduction to Sociology'),
        ('Introductory Business Ethics', 'Introductory Business Ethics'),
        ('Introductory Business Statistics', 'Introductory Business Statistics'),
        ('Introductory Statistics', 'Introductory Statistics'),
        ('LLPH', 'LLPH'),
        ('Macro Econ', 'Macro Econ'),
        ('Management', 'Management'),
        ('Managerial Accounting', 'Managerial Accounting'),
        ('Microbiology', 'Microbiology'),
        ('Micro Econ', 'Micro Econ'),
        ('Organic Chemistry', 'Organic Chemistry'),
        ('Organizational Behavior', 'Organizational Behavior'),
        ('Prealgebra', 'Prealgebra'),
        ('Precalc', 'Precalc'),
        ('Preparing for College Success', 'Preparing for College Success'),
        ('Principles of Finance', 'Principles of Finance'),
        ('Principles of Marketing', 'Principles of Marketing'),
        ('Psychology', 'Psychology'),
        ('University Physics (Calc)', 'University Physics (Calc)'),
        ('US History', 'US History'),
        ('Workplace Software and Skills', 'Workplace Software and Skills'),
        ('World History', 'World History'),
        ('Writing Guide', 'Writing Guide')
    ], blank=True, null=True)

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'


class Opportunity(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, max_length=18, verbose_name='Account ID', blank=True, null=True)
    record_type_id = models.CharField(max_length=18, verbose_name='Record Type ID', blank=True, null=True)
    name = models.CharField(max_length=120)
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

    class Meta:
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'


# A user will have many adoptions, but they represent a single book for a single school year
# The adoption is nested under the opportunity, which is nested under the contact

class Adoption(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    contact = models.ForeignKey(Contact, on_delete=models.DO_NOTHING)
    adoption_number = models.CharField(max_length=80)
    created_date = models.DateTimeField()
    last_modified_date = models.DateTimeField()
    system_modstamp = models.DateTimeField()
    last_activity_date = models.DateField(blank=True, null=True)
    class_start_date = models.DateField(blank=True, null=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.DO_NOTHING, max_length=18)
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

    class Meta:
        verbose_name = 'Adoption'
        verbose_name_plural = 'Adoptions'
