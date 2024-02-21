from salesforce import models

# An Account generally represents a School for OpenStax, but sometimes they can represent Partners, check the type field

class Account(models.SalesforceModel):
    name = models.CharField(db_column='Name', max_length=255, verbose_name='Account Name')
    type = models.CharField(db_column='Type', max_length=255, verbose_name='Account Type', help_text='Secondary classification of school (for eg. High School, Middle School, Community College, University)', choices=[('College/University (4)', 'College/University (4)'), ('Technical/Community College (2)', 'Technical/Community College (2)'), ('Career School/For-Profit (2)', 'Career School/For-Profit (2)'), ('For-Profit Tutoring', 'For-Profit Tutoring'), ('High School', 'High School'), ('Elementary School', 'Elementary School'), ('Middle/Junior High School', 'Middle/Junior High School'), ('K-12 School', 'K-12 School'), ('Other', 'Other'), ('Research Centers', 'Research Centers'), ('Intergovernmental', 'Intergovernmental'), ('Tutoring', 'Tutoring'), ('Programs', 'Programs'), ('Vendors', 'Vendors'), ('School District', 'School District'), ('Home School', 'Home School'), ('Parent', 'Parent'), ('Vocational', 'Vocational'), ('Child', 'Child')], blank=True, null=True)
    billing_street = models.TextField(db_column='BillingStreet', blank=True, null=True)
    billing_city = models.CharField(db_column='BillingCity', max_length=40, blank=True, null=True)
    billing_state = models.CharField(db_column='BillingState', max_length=80, verbose_name='Billing State/Province', blank=True, null=True)
    billing_postal_code = models.CharField(db_column='BillingPostalCode', max_length=20, verbose_name='Billing Zip/Postal Code', blank=True, null=True)
    billing_country = models.CharField(db_column='BillingCountry', max_length=80, blank=True, null=True)
    billing_state_code = models.CharField(db_column='BillingStateCode', max_length=10, verbose_name='Billing State/Province Code', blank=True, null=True)  # Too long choices skipped
    billing_country_code = models.CharField(db_column='BillingCountryCode', max_length=10, default='US', blank=True, null=True)  # Too long choices skipped
    billing_latitude = models.DecimalField(db_column='BillingLatitude', max_digits=18, decimal_places=15, blank=True, null=True)
    billing_longitude = models.DecimalField(db_column='BillingLongitude', max_digits=18, decimal_places=15, blank=True, null=True)
    billing_address = models.TextField(db_column='BillingAddress', sf_read_only=models.READ_ONLY, blank=True, null=True)  # This field type is a guess.
    phone = models.CharField(db_column='Phone', max_length=40, verbose_name='Account Phone', blank=True, null=True)
    website = models.URLField(db_column='Website', blank=True, null=True)
    photo_url = models.URLField(db_column='PhotoUrl', verbose_name='Photo URL', sf_read_only=models.READ_ONLY, blank=True, null=True)
    created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=models.READ_ONLY)
    created_by_id = models.CharField(db_column='CreatedById', max_length=18, verbose_name='Created By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=models.READ_ONLY)
    last_modified_by_id = models.CharField(db_column='LastModifiedById', max_length=18, verbose_name='Last Modified By ID', sf_read_only=models.READ_ONLY)  # References to missing tables: ['-User']
    last_activity_date = models.DateField(db_column='LastActivityDate', verbose_name='Last Activity', sf_read_only=models.READ_ONLY, blank=True, null=True)
    ipeds_id = models.CharField(db_column='IPEDS_ID__c', max_length=255, verbose_name='IPEDS ID', blank=True, null=True)
    nces_district_id = models.CharField(db_column='NCES_District_ID__c', max_length=50, verbose_name='NCES District ID', help_text='ID of the parent (school district)', blank=True, null=True)
    nces_district_id2 = models.CharField(db_column='NCES_District_ID2__c', max_length=1300, verbose_name='NCES District ID', sf_read_only=models.READ_ONLY, blank=True, null=True)
    continent = models.TextField(db_column='Continent__c', blank=True, null=True)
    lms = models.CharField(db_column='LMS__c', max_length=255, verbose_name='LMS', help_text='Learning Management System', choices=[('Blackboard', 'Blackboard'), ('Brightspace', 'Brightspace'), ('Canvas', 'Canvas'), ('D2L (Desire2Learn)', 'D2L (Desire2Learn)'), ('Learning Studio', 'Learning Studio'), ('Moodle', 'Moodle'), ('MoodleRooms', 'MoodleRooms'), ('Sakai', 'Sakai'), ('Other', 'Other')], blank=True, null=True)
    books_adopted = models.TextField(db_column='Books_Adopted__c', verbose_name='Books Adopted', blank=True, null=True)
    sheer_id_school_name = models.CharField(db_column='SheerID_School_Name__c', max_length=255, verbose_name='SheerID School Name', blank=True, null=True)
    nces_id = models.CharField(db_column='NCESID__c', max_length=255, verbose_name='NCESID', blank=True, null=True)

    class Meta(models.Model.Meta):
        db_table = 'Account'
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        # keyPrefix = '001'
