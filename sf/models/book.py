from salesforce import models


class Book(models.SalesforceModel):
    name = models.CharField(max_length=255)
    official_name = models.CharField(max_length=255, db_column="Official_Name__c")
    type = models.CharField(max_length=255, db_column="Book_Type__c")
    subject_areas = models.CharField(max_length=255, db_column="Subject_Area__c")
    website_url = models.URLField(max_length=255, db_column="OSC_URL__c")
    active_book = models.BooleanField(default=True, db_column="Active__c")

    class Meta:
        db_table = "Book__c"
        verbose_name = "Book"
        verbose_name_plural = "Books"
