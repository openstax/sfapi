from sf.connection import Salesforce

def get_adoptions(uuid):
    with Salesforce() as sf:
        adoptions = sf.query(
            f"SELECT \
                Id, \
                Base_Year__c, \
                School_Year__c, \
                Opportunity__r.Account.Name, \
                Confirmation_Type__c, \
                Students__c, \
                Savings__c, \
                How_Using__c, \
                Confirmation_Date__c \
                FROM Adoption__c \
                WHERE Opportunity__r.Contact__r.Accounts_UUID__c = '{uuid}'")['records']

        response = []
        for adoption in adoptions:
            response.append({
                'id': adoption['Id'],
                'base_year': adoption['Base_Year__c'],
                'school_year': adoption['School_Year__c'],
                'school': adoption['Opportunity__r']['Account']['Name'],
                'confirmation_type': adoption['Confirmation_Type__c'],
                'students': adoption['Students__c'],
                'savings': adoption['Savings__c'],
                'how_using': adoption['How_Using__c'],
                'confirmation_date': adoption['Confirmation_Date__c']
            })
        return response
