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
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=READ_ONLY, blank=True, null=True)
    last_modified_by = models.CharField(max_length=255, db_column='LastModifiedBy.alias', help_text='This is useful for ignoring integrations user modifications (like b2bma).')
    subject_interest = models.CharField(db_column='Subject_Interest__c', max_length=4099, verbose_name='Subject Interest', choices=[
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

    class Meta(models.Model.Meta):
        db_table = 'Contact'
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
