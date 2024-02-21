from salesforce import models

# An Account generally represents a School for OpenStax, but sometimes they can represent partners or other entities

class Account(models.SalesforceModel):
    name = models.CharField(db_column='Name', max_length=255, verbose_name='Account Name')
    type = models.CharField(db_column='Type', max_length=255, verbose_name='Account Type',
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
    billing_city = models.CharField(db_column='BillingCity', max_length=40, blank=True, null=True)
    billing_state = models.CharField(db_column='BillingState', max_length=80, blank=True, null=True)
    billing_country = models.CharField(db_column='BillingCountry', max_length=80, blank=True, null=True)
    billing_state_code = models.CharField(db_column='BillingStateCode', max_length=10,  blank=True, null=True)
    billing_country_code = models.CharField(db_column='BillingCountryCode', max_length=10,
                                            default='US', blank=True, null=True)
    created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=models.READ_ONLY)
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=models.READ_ONLY)
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity',
                                          sf_read_only=models.READ_ONLY, blank=True, null=True)
    lms = models.CharField(db_column='LMS__c', max_length=255, verbose_name='LMS',
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
    books_adopted = models.TextField(db_column='Books_Adopted__c', verbose_name='Books Adopted', blank=True, null=True)
    sheer_id_school_name = models.CharField(db_column='SheerID_School_Name__c', max_length=255,
                                            verbose_name='SheerID School Name', blank=True, null=True)
    ipeds_id = models.CharField(db_column='IPEDS_ID__c', max_length=255, verbose_name='IPEDS ID', blank=True, null=True)
    nces_district_id = models.CharField(db_column='NCES_District_ID__c', max_length=50, blank=True, null=True)
    nces_district_id2 = models.CharField(db_column='NCES_District_ID2__c', max_length=1300,
                                         sf_read_only=models.READ_ONLY, blank=True, null=True)
    nces_id = models.CharField(db_column='NCESID__c', max_length=255, verbose_name='NCESID', blank=True, null=True)

    class Meta(models.Model.Meta):
        db_table = 'Account'
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        # keyPrefix = '001'
