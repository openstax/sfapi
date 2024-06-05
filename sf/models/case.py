from salesforce import models

class Case(models.SalesforceModel):
    subject = models.CharField(db_column='Subject', max_length=255, verbose_name='Subject')
    description = models.TextField(db_column='Description', verbose_name='Description')
    product = models.CharField(db_column='Product__c', max_length=255, verbose_name='Product', blank=True, null=True)
    feature = models.CharField(db_column='Feature__c', max_length=255, verbose_name='Feature', blank=True, null=True)
    issue = models.CharField(db_column='Issue__c', max_length=255, verbose_name='Issue', blank=True, null=True)

    class Meta(models.Model.Meta):
        db_table = 'Case'
        verbose_name = 'Case'
        verbose_name_plural = 'Cases'
