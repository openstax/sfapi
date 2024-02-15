from salesforce import models
from salesforce.models import SalesforceModel, READ_ONLY, NOT_CREATEABLE, DO_NOTHING, DEFAULTED_ON_CREATE
from .account import Account

class Contact(SalesforceModel):
    first_name = models.CharField(max_length=255, db_column='FirstName')
    last_name = models.CharField(max_length=255, db_column='LastName')
    full_name = models.CharField(max_length=255, db_column='Name')
    role = models.CharField(max_length=255, db_column='Role__c')
    position = models.CharField(max_length=255, db_column='Position__c')
    title = models.CharField(max_length=128, db_column='Title')
    account = models.ForeignKey(Account, models.DO_NOTHING, db_column='AccountId', verbose_name='Account ID',blank=True, null=True)  # Master Detail Relationship *
    adoption_status = models.CharField(max_length=255, db_column='Adoption_Status__c')
    adoptions_json = models.TextField(db_column='AdoptionsJSON__c')
    subject_interest = models.TextField(db_column='Subject_Interest__c')
    verification_status = models.CharField(max_length=255, db_column='FV_Status__c')
    reject_reason = models.CharField(max_length=255, db_column='Reject_Reason__c')
    accounts_uuid = models.CharField(max_length=255, db_column='Accounts_UUID__c')
    accounts_id = models.CharField(max_length=255, db_column='Accounts_ID__c', help_text='Prioritize using Accounts UUID (uuid) over this for identification with accounts users.')
    signup_date = models.DateTimeField(db_column='Signup_Date__c')
    lead_source = models.CharField(max_length=255, db_column='LeadSource')
    lms = models.CharField(max_length=255, db_column='LMS__c')
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=READ_ONLY, blank=True, null=True)
    last_modified_by = models.CharField(max_length=255, db_column='LastModifiedBy.alias', help_text='This is useful for ignoring integrations user modifications (like b2bma).')


# class Contact(SalesforceModel):
#     account = models.ForeignKey(Account, models.DO_NOTHING, db_column='AccountId', verbose_name='Account ID', blank=True, null=True)  # Master Detail Relationship *
#     last_name = models.CharField(db_column='LastName', max_length=80)
#     first_name = models.CharField(db_column='FirstName', max_length=40, blank=True, null=True)
#     salutation = models.CharField(db_column='Salutation', max_length=40, choices=[('Mr.', 'Mr.'), ('Ms.', 'Ms.'), ('Mrs.', 'Mrs.'), ('Dr.', 'Dr.'), ('Prof.', 'Prof.'), ('Mx.', 'Mx.')], blank=True, null=True)
#     middle_name = models.CharField(db_column='MiddleName', max_length=40, blank=True, null=True)
#     suffix = models.CharField(db_column='Suffix', max_length=40, blank=True, null=True)
#     name = models.CharField(db_column='Name', max_length=121, verbose_name='Full Name', sf_read_only=READ_ONLY)
#     phone = models.CharField(db_column='Phone', max_length=40, verbose_name='Business Phone', blank=True, null=True)
#     email = models.EmailField(db_column='Email', blank=True, null=True)
#     title = models.CharField(db_column='Title', max_length=128, blank=True, null=True)
#     lead_source = models.CharField(db_column='LeadSource', max_length=255, help_text='First point of contact', choices=[('Customer Service Ticket', 'Customer Service Ticket'), ('Phone', 'Phone'), ('Chat', 'Chat'), ('Conference', 'Conference'), ('Comp Request', 'Comp Request'), ('Partner', 'Partner'), ('Newsletter', 'Newsletter'), ('Adoption Form', 'Adoption Form'), ('Referral Form', 'Referral Form'), ('Renewal Form', 'Renewal Form'), ('Donation', 'Donation'), ('Web', 'Web'), ('Webinar', 'Webinar'), ('Institutional Relations', 'Institutional Relations'), ('Followup Form', 'Followup Form'), ('Student', 'Student'), ('Email', 'Email'), ('Tutor Signup', 'Tutor Signup'), ('Interest Form', 'Interest Form'), ('Rover', 'Rover'), ('Testimonial', 'Testimonial'), ('Renewal Popup', 'Renewal Popup'), ('Partner Marketplace', 'Partner Marketplace'), ('Offsite Go-To-Webinar Form', 'Offsite Go-To-Webinar Form'), ('Website Tutor Webinar Form', 'Website Tutor Webinar Form'), ('Offsite Creator Feast Registration Form', 'Offsite Creator Feast Registration Form'), ('Manual List Adds', 'Manual List Adds'), ('Website E-Newsletter Sign-Up Form', 'Website E-Newsletter Sign-Up Form'), ('Website Institutional Partner Sign Up Form', 'Website Institutional Partner Sign Up Form'), ('Website Contact Us Form', 'Website Contact Us Form'), ('TSR', 'TSR'), ('Facebook Ads', 'Facebook Ads'), ('LinkedIn Ads', 'LinkedIn Ads'), ('BMG Import', 'BMG Import'), ('Account Creation', 'Account Creation')], blank=True, null=True)
#     has_opted_out_of_email = models.BooleanField(db_column='HasOptedOutOfEmail', verbose_name='Email Opt Out', default=False, help_text="Don't send emails")
#     do_not_call = models.BooleanField(db_column='DoNotCall', default=False)
#     created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=READ_ONLY)
#     created_by_id = models.CharField(db_column='CreatedById', max_length=18, verbose_name='Created By ID', sf_read_only=READ_ONLY)  # References to missing tables: ['-User']
#     last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=READ_ONLY)
#     last_modified_by_id = models.CharField(db_column='LastModifiedById', max_length=18, verbose_name='Last Modified By ID', sf_read_only=READ_ONLY)  # References to missing tables: ['-User']
#     system_modstamp = models.DateTimeField(db_column='SystemModstamp', sf_read_only=READ_ONLY)
#     last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=READ_ONLY, blank=True, null=True)
#     last_curequest_date = models.DateTimeField(db_column='LastCURequestDate', verbose_name='Last Stay-in-Touch Request Date', sf_read_only=READ_ONLY, blank=True, null=True)
#     last_cuupdate_date = models.DateTimeField(db_column='LastCUUpdateDate', verbose_name='Last Stay-in-Touch Save Date', sf_read_only=READ_ONLY, blank=True, null=True)
#     last_viewed_date = models.DateTimeField(db_column='LastViewedDate', sf_read_only=READ_ONLY, blank=True, null=True)
#     last_referenced_date = models.DateTimeField(db_column='LastReferencedDate', sf_read_only=READ_ONLY, blank=True, null=True)
#     email_bounced_reason = models.CharField(db_column='EmailBouncedReason', max_length=255, blank=True, null=True)
#     email_bounced_date = models.DateTimeField(db_column='EmailBouncedDate', blank=True, null=True)
#     is_email_bounced = models.BooleanField(db_column='IsEmailBounced', sf_read_only=READ_ONLY, default=False)
#     photo_url = models.URLField(db_column='PhotoUrl', verbose_name='Photo URL', sf_read_only=READ_ONLY, blank=True, null=True)
#     pronouns = models.CharField(db_column='Pronouns', max_length=255, choices=[('He/Him', 'He/Him'), ('She/Her', 'She/Her'), ('They/Them', 'They/Them'), ('He/They', 'He/They'), ('She/They', 'She/They'), ('Not Listed', 'Not Listed')], blank=True, null=True)
#     gender_identity = models.CharField(db_column='GenderIdentity', max_length=255, choices=[('Male', 'Male'), ('Female', 'Female'), ('Nonbinary', 'Nonbinary'), ('Not Listed', 'Not Listed')], blank=True, null=True)
#     engagement_score_id = models.CharField(db_column='EngagementScoreId', max_length=18, verbose_name='Behavior Score ID', sf_read_only=READ_ONLY, blank=True, null=True)  # References to missing tables: ['-EngagementScore']
#     books_adopted = models.TextField(db_column='Books_Adopted__c', verbose_name='Books Adopted', default='None', help_text='List of books adopted', blank=True, null=True)
#     self_reported_school_name = models.CharField(db_column='Self_Reported_School_Name__c', max_length=1300, verbose_name='Self Reported School Name', sf_read_only=READ_ONLY, blank=True, null=True)
#     email_alt = models.EmailField(db_column='Email_alt__c', verbose_name='Email alt', blank=True, null=True)
#     lead_notes = models.TextField(db_column='Lead_Notes__c', verbose_name='Lead Notes', help_text='Notes made on the original lead before conversion', blank=True, null=True)
#     adoption_status = models.CharField(db_column='Adoption_Status__c', max_length=255, verbose_name='Adoption Status', default='Not Adopter', choices=[('Not Adopter', 'Not Adopter'), ('Current Adopter', 'Current Adopter'), ('Past Adopter', 'Past Adopter'), ('Future Adopter', 'Future Adopter')], blank=True, null=True)
#     assignable_interest = models.CharField(db_column='Assignable_Interest__c', max_length=255, verbose_name='Assignable Interest', choices=[('Interested', 'Interested'), ('Demo', 'Demo'), ('Fully Integrated', 'Fully Integrated')], blank=True, null=True)
#     position_t = models.CharField(db_column='PositionT__c', max_length=255, verbose_name='PositionT', help_text='Text version of position for exporting to Pardot', blank=True, null=True)
#     number_of_books_adopted = models.DecimalField(db_column='Number_of_books_adopted__c', max_digits=18, decimal_places=0, verbose_name='Number of Books Adopted', blank=True, null=True)
#     accounts_uuid = models.CharField(db_column='Accounts_UUID__c', unique=True, max_length=255, verbose_name='Accounts UUID', help_text='ID used in OS Accounts', blank=True, null=True)
#     partner_contact = models.BooleanField(db_column='Partner_Contact__c', verbose_name='Partner Contact', sf_read_only=READ_ONLY, help_text='True if at a partner')
#     school_type = models.CharField(db_column='School_Type__c', max_length=1300, verbose_name='School Type', sf_read_only=READ_ONLY, help_text='School Type (2 year, 4 year)', blank=True, null=True)
#     position = models.CharField(db_column='Position__c', max_length=4099, choices=[('Accounting', 'Accounting'), ('Adjunct Faculty', 'Adjunct Faculty'), ('Administrator', 'Administrator'), ('Bookstore', 'Bookstore'), ('Department Head', 'Department Head'), ('Faculty', 'Faculty'), ('Grad Student', 'Grad Student'), ('Home School Teacher', 'Home School Teacher'), ('Instructional Designer', 'Instructional Designer'), ('Instructor', 'Instructor'), ('Leads', 'Leads'), ('Librarian', 'Librarian'), ('Marketer', 'Marketer'), ('Marketing', 'Marketing'), ('Other', 'Other'), ('Partner', 'Partner'), ('Partner Portal User', 'Partner Portal User'), ('Primary', 'Primary'), ('Researcher', 'Researcher'), ('Student', 'Student'), ('Teaching Assistant', 'Teaching Assistant'), ('Tutor', 'Tutor')], blank=True, null=True)
#     reject_reason = models.CharField(db_column='Reject_Reason__c', max_length=255, verbose_name='Reject Reason', choices=[('Bad School Info', 'Bad School Info'), ('Homeschool no info', 'Homeschool no info'), ('Unverifiable', 'Unverifiable'), ('Duplicate', 'Duplicate')], blank=True, null=True)
#     last_in_touch_date = models.DateField(db_column='Last_In_Touch_Date__c', verbose_name='Last In Touch Date', help_text='Most recent date the contact was in touch with us', blank=True, null=True)
#     accounts_id = models.CharField(db_column='Accounts_ID__c', max_length=100, verbose_name='OS Accounts ID', help_text='The ID in OS Accounts', blank=True, null=True)
#     initial_adoption_date = models.DateField(db_column='Initial_Adoption_Date__c', verbose_name='Initial Adoption Date', help_text='The date we first learned of their adoption', blank=True, null=True)
#     pi_needs_score_synced = models.BooleanField(db_column='pi__Needs_Score_Synced__c', verbose_name='Needs Score Synced', default=False, help_text='Pardot')
#     pi_pardot_last_scored_at = models.DateTimeField(db_column='pi__Pardot_Last_Scored_At__c', verbose_name='Account Engagement Last Scored At', blank=True, null=True)
#     pi_campaign = models.CharField(db_column='pi__campaign__c', max_length=255, verbose_name='Account Engagement Campaign', blank=True, null=True)
#     pi_comments = models.TextField(db_column='pi__comments__c', verbose_name='Account Engagement Comments', blank=True, null=True)
#     pi_conversion_date = models.DateTimeField(db_column='pi__conversion_date__c', verbose_name='Account Engagement Conversion Date', blank=True, null=True)
#     pi_conversion_object_name = models.CharField(db_column='pi__conversion_object_name__c', max_length=255, verbose_name='Conversion Object Name', blank=True, null=True)
#     pi_conversion_object_type = models.CharField(db_column='pi__conversion_object_type__c', max_length=255, verbose_name='Conversion Object Type', blank=True, null=True)
#     pi_created_date = models.DateTimeField(db_column='pi__created_date__c', verbose_name='Account Engagement Created Date', blank=True, null=True)
#     pi_first_activity = models.DateTimeField(db_column='pi__first_activity__c', verbose_name='Account Engagement First Activity', blank=True, null=True)
#     pi_first_search_term = models.CharField(db_column='pi__first_search_term__c', max_length=255, verbose_name='Account Engagement First Referrer Query', blank=True, null=True)
#     pi_first_search_type = models.CharField(db_column='pi__first_search_type__c', max_length=255, verbose_name='Account Engagement First Referrer Type', blank=True, null=True)
#     pi_first_touch_url = models.TextField(db_column='pi__first_touch_url__c', verbose_name='Account Engagement First Referrer', blank=True, null=True)
#     anniversary_date = models.DateField(db_column='Anniversary_Date__c', verbose_name='Anniversary Date', sf_read_only=READ_ONLY, blank=True, null=True)
#     school_name = models.CharField(db_column='School_Name__c', max_length=1300, verbose_name='School Name', sf_read_only=READ_ONLY, blank=True, null=True)
#     pi_grade = models.CharField(db_column='pi__grade__c', max_length=10, verbose_name='Account Engagement Grade', blank=True, null=True)
#     pi_last_activity = models.DateTimeField(db_column='pi__last_activity__c', verbose_name='Account Engagement Last Activity', blank=True, null=True)
#     pi_notes = models.TextField(db_column='pi__notes__c', verbose_name='Account Engagement Notes', blank=True, null=True)
#     pi_pardot_hard_bounced = models.BooleanField(db_column='pi__pardot_hard_bounced__c', verbose_name='Account Engagement Hard Bounced', default=False)
#     pi_score = models.DecimalField(db_column='pi__score__c', max_digits=18, decimal_places=0, verbose_name='Account Engagement Score', blank=True, null=True)
#     faculty_confirmed_date = models.DateField(db_column='Faculty_Confirmed_Date__c', verbose_name='Faculty Confirmed Date', help_text='Date faculty status was confirmed', blank=True, null=True)
#     last_osweb_login_date = models.DateField(db_column='Last_OSweb_Login_Date__c', verbose_name='Last OSweb Login Date', blank=True, null=True)
#     lms = models.CharField(db_column='LMS__c', max_length=255, verbose_name='LMS', choices=[('Blackboard', 'Blackboard'), ('Brightspace', 'Brightspace'), ('Canvas', 'Canvas'), ('D2L (Desire2Learn)', 'D2L (Desire2Learn)'), ('Learning Studio', 'Learning Studio'), ('Moodle', 'Moodle'), ('MoodleRooms', 'MoodleRooms'), ('Sakai', 'Sakai'), ('Other', 'Other')], blank=True, null=True)
#     number_of_subjects = models.DecimalField(db_column='Number_of_Subjects__c', max_digits=18, decimal_places=0, verbose_name='Number of Subjects', help_text='Number of subjects contact is interested in', blank=True, null=True)
#     how_did_you_hear = models.CharField(db_column='How_did_you_Hear__c', max_length=255, verbose_name='How did you Hear?', choices=[('Web Search', 'Web Search'), ('Colleague', 'Colleague'), ('Conference', 'Conference'), ('Email', 'Email'), ('Facebook', 'Facebook'), ('Twitter', 'Twitter'), ('Webinar', 'Webinar'), ('Partner organization', 'Partner organization')], blank=True, null=True)
#     all_emails = models.CharField(db_column='All_Emails__c', max_length=255, verbose_name='All Emails', help_text='All emails associated with contact', blank=True, null=True)
#     newsletter_opt_out = models.BooleanField(db_column='Newsletter_Opt_Out__c', verbose_name='Newsletter Opt Out', default=False, help_text='True if they do NOT want newsletter')
#     lms_option = models.CharField(db_column='LMS_Option__c', max_length=255, verbose_name='LMS Option', choices=[('Blackboard', 'Blackboard'), ('Canvas', 'Canvas'), ('D2L (Desire2Learn)', 'D2L (Desire2Learn)'), ('Moodle', 'Moodle'), ('Other', 'Other')], blank=True, null=True)
#     total_mql_score = models.DecimalField(db_column='Total_MQL_Score__c', max_digits=18, decimal_places=0, verbose_name='Total MQL Score', blank=True, null=True)
#     total_sql_score = models.DecimalField(db_column='Total_SQL_Score__c', max_digits=18, decimal_places=0, verbose_name='Total SQL Score', blank=True, null=True)
#     total_potential_score = models.DecimalField(db_column='Total_Potential_Score__c', max_digits=18, decimal_places=0, verbose_name='Total Potential Score', sf_read_only=READ_ONLY, blank=True, null=True)
#     last_page_action_completed = models.TextField(db_column='Last_Page_Action_Completed__c', verbose_name='Last Page Action Completed', blank=True, null=True)
#     last_site_action_completed = models.TextField(db_column='Last_Site_Action_Completed__c', verbose_name='Last Site Action Completed', blank=True, null=True)
#     last_resource_download_date = models.DateField(db_column='Last_Resource_Download_Date__c', verbose_name='Last Resource Download Date', blank=True, null=True)
#     adoptions_json = models.TextField(db_column='AdoptionsJSON__c', verbose_name='AdoptionsJSON', blank=True, null=True)
#     fv_status = models.CharField(db_column='FV_Status__c', max_length=255, verbose_name='FV Status', choices=[('no_faculty_info', 'No Faculty Info'), ('incomplete_signup', 'Incomplete Signup'), ('pending_faculty', 'Pending'), ('rejected_by_sheerid', 'Rejected by SheerID'), ('rejected_faculty', 'Rejected'), ('confirmed_faculty', 'Confirmed'), ('pending_sheerid', 'Pending SheerID')], blank=True, null=True)
#     role = models.CharField(db_column='Role__c', max_length=255, choices=[('Student', 'Student'), ('Instructor', 'Instructor')], blank=True, null=True)
#     who_chooses_books = models.CharField(db_column='who_chooses_books__c', max_length=255, verbose_name='who chooses books', choices=[('Instructor', 'Instructor'), ('Committee', 'Committee'), ('Coordinator', 'Coordinator')], blank=True, null=True)
#     signup_date = models.DateTimeField(db_column='Signup_Date__c', verbose_name='Signup Date', help_text='The date and time the user signed up for an OpenStax Account', blank=True, null=True)
#     subject_interest = models.CharField(db_column='Subject_Interest__c', max_length=4099, verbose_name='Subject Interest', choices=[
#         ('Algebra and Trigonometry', 'Algebra and Trigonometry'),
#         ('American Government', 'American Government'),
#         ('Anatomy & Physiology', 'Anatomy & Physiology'),
#         ('Anthropology', 'Anthropology'),
#         ('AP Bio', 'AP Bio'),
#         ('AP Macro Econ', 'AP Macro Econ'),
#         ('AP Micro Econ', 'AP Micro Econ'),
#         ('AP Physics', 'AP Physics'),
#         ('Astronomy', 'Astronomy'),
#         ('Basic College Math', 'Basic College Math'),
#         ('Biology', 'Biology'),
#         ('Business Ethics', 'Business Ethics'),
#         ('Business Law', 'Business Law'),
#         ('Business Law I Essentials', 'Business Law I Essentials'),
#         ('Business Statistics', 'Business Statistics'),
#         ('Calculus', 'Calculus'),
#         ('Career Readiness', 'Career Readiness'),
#         ('Chem: Atoms First', 'Chem: Atoms First'),
#         ('Chemistry', 'Chemistry'),
#         ('College Algebra', 'College Algebra'),
#         ('College Algebra with Corequisite Support', 'College Algebra with Corequisite Support'),
#         ('College Physics (Algebra)', 'College Physics (Algebra)'),
#         ('College Success', 'College Success'),
#         ('College Success Concise', 'College Success Concise'),
#         ('Concepts of Bio (non-majors)', 'Concepts of Bio (non-majors)'),
#         ('Contemporary Math', 'Contemporary Math'),
#         ('Economics', 'Economics'),
#         ('Elementary Algebra', 'Elementary Algebra'),
#         ('Entrepreneurship', 'Entrepreneurship'),
#         ('Financial Accounting', 'Financial Accounting'),
#         ('Finite Algebra', 'Finite Algebra'),
#         ('HS Physics', 'HS Physics'),
#         ('HS Statistics', 'HS Statistics'),
#         ('Intermediate Algebra', 'Intermediate Algebra'),
#         ('Introduction to Business', 'Introduction to Business'),
#         ('Introduction to Intellectual Property', 'Introduction to Intellectual Property'),
#         ('Introduction to Philosophy', 'Introduction to Philosophy'),
#         ('Introduction to Political Science', 'Introduction to Political Science'),
#         ('Introduction to Sociology', 'Introduction to Sociology'),
#         ('Introductory Business Ethics', 'Introductory Business Ethics'),
#         ('Introductory Business Statistics', 'Introductory Business Statistics'),
#         ('Introductory Statistics', 'Introductory Statistics'),
#         ('LLPH', 'LLPH'),
#         ('Macro Econ', 'Macro Econ'),
#         ('Management', 'Management'),
#         ('Managerial Accounting', 'Managerial Accounting'),
#         ('Microbiology', 'Microbiology'),
#         ('Micro Econ', 'Micro Econ'),
#         ('Organic Chemistry', 'Organic Chemistry'),
#         ('Organizational Behavior', 'Organizational Behavior'),
#         ('Prealgebra', 'Prealgebra'),
#         ('Precalc', 'Precalc'),
#         ('Preparing for College Success', 'Preparing for College Success'),
#         ('Principles of Finance', 'Principles of Finance'),
#         ('Principles of Marketing', 'Principles of Marketing'),
#         ('Psychology', 'Psychology'),
#         ('University Physics (Calc)', 'University Physics (Calc)'),
#         ('US History', 'US History'),
#         ('Workplace Software and Skills', 'Workplace Software and Skills'),
#         ('World History', 'World History'),
#         ('Writing Guide', 'Writing Guide')
#     ], blank=True, null=True)
#
#     class Meta(models.Model.Meta):
#         db_table = 'Contact'
#         verbose_name = 'Contact'
#         verbose_name_plural = 'Contacts'
        # keyPrefix = '003'
