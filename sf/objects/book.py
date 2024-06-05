from sf.connection import Salesforce

def get_books():
    with Salesforce() as sf:
        books = sf.query(
            f"SELECT \
                Id, \
                Name, \
                Official_Name__c, \
                Subject_Area__c, \
                OSC_URL__c, \
                Active__c, \
                Subject__c \
                FROM Book__c")['records']

        response = []
        for book in books:
            response.append({
                'id': book['Id'],
                'name': book['Name'],
                'official_name': book['Official_Name__c'],
                'subject_areas': book['Subject_Area__c'],
                'website_url': book['OSC_URL__c'],
                'active_book': book['Active__c'],
            })
        return response
