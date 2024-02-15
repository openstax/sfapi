from salesforce import models


class Book(models.SalesforceModel):
    name = models.CharField(max_length=255)
    official_name = models.CharField(max_length=255, db_column='Official_Name__c')
    type = models.CharField(max_length=255, db_column='Book_Type__c')
    subject_areas = models.CharField(max_length=255, db_column='OSWeb_Group__c')

    class Meta:
        db_table = 'Book__c'
