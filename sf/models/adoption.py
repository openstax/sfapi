from salesforce import models
from .contact import Contact
from .opportunity import Opportunity

# A user will have many adoptions, but they represent a single book for a single school year
# The adoption is nested under the opportunity, which is nested under the contact

class Adoption(models.SalesforceModel):
    contact = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, sf_read_only=models.READ_ONLY, db_column='Opportunity__r.Contact__c')
    adoption_number = models.CharField(db_column='Name', max_length=80, sf_read_only=models.READ_ONLY)
    created_date = models.DateTimeField(db_column='CreatedDate', sf_read_only=models.READ_ONLY)
    last_modified_date = models.DateTimeField(db_column='LastModifiedDate', sf_read_only=models.READ_ONLY)
    system_modstamp = models.DateTimeField(db_column='SystemModstamp', sf_read_only=models.READ_ONLY)
    last_activity_date = models.DateField(db_column='LastActivityDate', sf_read_only=models.READ_ONLY, blank=True,
                                          null=True)
    class_start_date = models.DateField(db_column='Class_Start_Date__c', blank=True, null=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.DO_NOTHING, sf_read_only=models.READ_ONLY, db_column='Opportunity__c', max_length=18)
    confirmation_date = models.DateField(db_column='Confirmation_Date__c', blank=True, null=True)
    name = models.CharField(db_column='Name__c', max_length=255, blank=True, null=True)
    base_year = models.DecimalField(db_column='Base_Year__c', max_digits=4, decimal_places=0, blank=True, null=True)
    adoption_type = models.CharField(db_column='Adoption_Type__c', max_length=255, verbose_name='Adoption Type',
                                     choices=[
                                         ('Faculty/Teacher Adoption', 'Faculty/Teacher Adoption'),
                                         ('School Adoption', 'School Adoption')
                                     ])
    students = models.DecimalField(db_column='Students__c', max_digits=18, decimal_places=0, blank=True, null=True)
    school_year = models.CharField(db_column='School_Year__c', max_length=9, verbose_name='School Year')
    terms_used = models.CharField(db_column='Terms_Used__c', max_length=255, verbose_name='Terms Used',
                                  choices=[
                                      ('Fall', 'Fall'),
                                      ('Spring', 'Spring'),
                                      ('Both', 'Both'),
                                      ('Winter', 'Winter'),
                                      ('Summer', 'Summer')
                                  ], blank=True, null=True)
    confirmation_type = models.CharField(db_column='Confirmation_Type__c', max_length=255,
                                         verbose_name='Confirmation Type', default='OpenStax Confirmed Adoption',
                                         choices=[
                                             ('OpenStax Confirmed Adoption', 'OpenStax Confirmed Adoption'),
                                             ('Third Party Confirmed Adoption', 'Third Party Confirmed Adoption'),
                                             ('User Behavior Informed Adoption', 'User Behavior Informed Adoption')
                                         ])
    how_using = models.CharField(db_column='How_Using__c', max_length=255, verbose_name='How Using', choices=[
        ('As the core textbook for my course', 'As the core textbook for my course'),
        ('As an optional/recommended textbook for my course', 'As an optional/recommended textbook for my course'),
        ('To teach, tutor, or support students outside of a course setting',
         'To teach, tutor, or support students outside of a course setting'),
        ('For my own knowledge or other work', 'For my own knowledge or other work')
    ], blank=True, null=True)
    savings = models.DecimalField(db_column='Savings__c', max_digits=18, decimal_places=2,
                                  sf_read_only=models.READ_ONLY, blank=True, null=True)

    class Meta(models.Model.Meta):
        db_table = 'Adoption__c'
        verbose_name = 'Adoption'
        verbose_name_plural = 'Adoptions'
