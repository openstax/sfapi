from sf.connection import Salesforce

def get_contact(uuid):
    with Salesforce() as sf:
        contact = sf.query(
            f"SELECT \
                Id, \
                Name, \
                Account.Name, \
                Role__c, \
                Position__c, \
                Adoption_Status__c, \
                Subject_Interest__c, \
                LMS__c, \
                Accounts_UUID__c, \
                FV_Status__c, \
                Signup_Date__c, \
                LeadSource \
                FROM Contact \
                WHERE Accounts_UUID__c = '{uuid}'")['records'][0]

        response = {
            'id': contact['Id'],
            'name': contact['Name'],
            'school': contact['Account']['Name'],
            'role': contact['Role__c'],
            'position': contact['Position__c'],
            'adoption_status': contact['Adoption_Status__c'],
            'subject_interest': contact['Subject_Interest__c'],
            'lms': contact['LMS__c'],
            'accounts_uuid': contact['Accounts_UUID__c'],
            'verification_status': contact['FV_Status__c'],
            'signup_date': contact['Signup_Date__c'],
            'lead_source': contact['LeadSource']
        }
        return response
